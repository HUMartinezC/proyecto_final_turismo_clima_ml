from botocore.exceptions import ClientError

from tourism_weather_ml.aws.clients import AwsClients
from tourism_weather_ml.config import Settings


class AwsProvisioner:
    """Creates the minimal AWS data architecture required by the project."""

    def __init__(self, settings: Settings, clients: AwsClients) -> None:
        self.settings = settings
        self.clients = clients

    def provision(self, dry_run: bool = True) -> list[str]:
        bucket = self.settings.s3_bucket_name or "<S3_BUCKET_NAME>"
        actions = [
            "validate AWS identity with STS",
            f"ensure S3 bucket is available: {bucket}",
            f"ensure S3 lake prefixes: {self._lake_prefixes()}",
            f"ensure Glue database is available: {self.settings.glue_database}",
            f"ensure Athena workgroup is available: {self.settings.athena_workgroup}",
            self._rds_action(),
            self._docdb_action(),
            self._lambda_action(),
            self._kafka_action(),
        ]
        if dry_run:
            return [f"DRY-RUN {action}" for action in actions]

        self._validate_identity()
        self._ensure_bucket()
        self._ensure_glue_database()
        self._ensure_athena_workgroup()
        mariadb_created = self._ensure_mariadb_instance()
        if mariadb_created:
            self._wait_for_mariadb_available()
        return actions

    def _validate_identity(self) -> None:
        self.clients.sts.get_caller_identity()

    def _ensure_bucket(self) -> None:
        if not self.settings.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is required to create the data lake bucket.")

        s3 = self.clients.s3
        bucket = self.settings.s3_bucket_name
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            create_args: dict[str, object] = {"Bucket": bucket}
            if self.settings.aws_region != "us-east-1":
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.settings.aws_region
                }
            s3.create_bucket(**create_args)
            s3.get_waiter("bucket_exists").wait(
                Bucket=bucket,
                WaiterConfig={"Delay": 5, "MaxAttempts": 24},
            )

        for prefix in (
            self.settings.s3_bronze_prefix,
            self.settings.s3_silver_prefix,
            self.settings.s3_gold_prefix,
        ):
            s3.put_object(Bucket=bucket, Key=f"{prefix}/")

        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                    }
                ]
            },
        )
        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )

    def _ensure_glue_database(self) -> None:
        glue = self.clients.glue
        try:
            glue.get_database(Name=self.settings.glue_database)
        except glue.exceptions.EntityNotFoundException:
            glue.create_database(DatabaseInput={"Name": self.settings.glue_database})
        self._wait_for_glue_database()

    def _ensure_athena_workgroup(self) -> None:
        if not self.settings.athena_results_s3_uri:
            raise ValueError("ATHENA_RESULTS_S3_URI is required to configure Athena.")

        athena = self.clients.athena
        try:
            athena.get_work_group(WorkGroup=self.settings.athena_workgroup)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"InvalidRequestException", "ResourceNotFoundException"}:
                raise
            athena.create_work_group(
                Name=self.settings.athena_workgroup,
                Configuration={
                    "ResultConfiguration": {
                        "OutputLocation": self.settings.athena_results_s3_uri,
                    },
                    "EnforceWorkGroupConfiguration": False,
                    "PublishCloudWatchMetricsEnabled": True,
                },
                Description="Tourism-weather ML Athena workgroup",
            )
        self._wait_for_athena_workgroup()

    def _lake_prefixes(self) -> str:
        return ", ".join(
            (
                self.settings.s3_bronze_prefix,
                self.settings.s3_silver_prefix,
                self.settings.s3_gold_prefix,
            )
        )

    def _rds_action(self) -> str:
        public_status = "public" if self.settings.rds_publicly_accessible else "private"
        return (
            f"ensure RDS MariaDB test instance: {self.settings.rds_instance_identifier} "
            f"({self.settings.rds_instance_class}, {public_status}, port {self.settings.rds_port}) "
            "and wait until available"
        )

    def _docdb_action(self) -> str:
        if self.settings.docdb_uri:
            return "validate configured DocumentDB connection URI"
        return "skip DocumentDB creation: requires VPC/subnet/security group sizing decisions"

    def _lambda_action(self) -> str:
        if self.settings.lambda_role_arn:
            return f"prepare Lambda function: {self.settings.lambda_function_name}"
        return "skip Lambda creation: LAMBDA_ROLE_ARN is not configured"

    def _kafka_action(self) -> str:
        if self.settings.kafka_bootstrap_servers:
            return "validate configured Kafka/MSK bootstrap servers"
        return "skip MSK creation: requires VPC/subnet/security group and broker sizing decisions"

    def _ensure_mariadb_instance(self) -> bool:
        if self.settings.rds_engine != "mariadb":
            return False
        if not self.settings.rds_user or not self.settings.rds_password:
            raise ValueError("RDS_USER and RDS_PASSWORD are required to create MariaDB in RDS.")

        rds = self.clients.rds
        try:
            rds.describe_db_instances(
                DBInstanceIdentifier=self.settings.rds_instance_identifier,
            )
            self._wait_for_mariadb_available()
            return False
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code != "DBInstanceNotFound":
                raise

        security_group_id = self._ensure_public_mariadb_security_group()
        rds.create_db_instance(
            DBInstanceIdentifier=self.settings.rds_instance_identifier,
            DBInstanceClass=self.settings.rds_instance_class,
            Engine="mariadb",
            AllocatedStorage=self.settings.rds_allocated_storage,
            StorageType="gp3",
            DBName=self.settings.rds_database,
            MasterUsername=self.settings.rds_user,
            MasterUserPassword=self.settings.rds_password,
            Port=self.settings.rds_port,
            PubliclyAccessible=self.settings.rds_publicly_accessible,
            VpcSecurityGroupIds=[security_group_id],
            BackupRetentionPeriod=0,
            DeletionProtection=False,
            AutoMinorVersionUpgrade=True,
            CopyTagsToSnapshot=True,
            Tags=[
                {"Key": "Project", "Value": self.settings.project_name},
                {"Key": "Environment", "Value": self.settings.environment},
                {"Key": "Purpose", "Value": "test"},
            ],
        )
        return True

    def _ensure_public_mariadb_security_group(self) -> str:
        ec2 = self.clients.ec2
        vpc_id = self._default_vpc_id()
        response = ec2.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": [self.settings.rds_security_group_name]},
                {"Name": "vpc-id", "Values": [vpc_id]},
            ]
        )
        if response["SecurityGroups"]:
            security_group_id = response["SecurityGroups"][0]["GroupId"]
        else:
            created = ec2.create_security_group(
                GroupName=self.settings.rds_security_group_name,
                Description="Public MariaDB access for tourism-weather ML test environment",
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        "ResourceType": "security-group",
                        "Tags": [
                            {"Key": "Name", "Value": self.settings.rds_security_group_name},
                            {"Key": "Project", "Value": self.settings.project_name},
                            {"Key": "Environment", "Value": self.settings.environment},
                        ],
                    }
                ],
            )
            security_group_id = created["GroupId"]

        self._allow_public_mariadb_ingress(security_group_id)
        return security_group_id

    def _allow_public_mariadb_ingress(self, security_group_id: str) -> None:
        ec2 = self.clients.ec2
        try:
            ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": self.settings.rds_port,
                        "ToPort": self.settings.rds_port,
                        "IpRanges": [
                            {
                                "CidrIp": "0.0.0.0/0",
                                "Description": "Public MariaDB test access",
                            }
                        ],
                    }
                ],
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code != "InvalidPermission.Duplicate":
                raise

    def _default_vpc_id(self) -> str:
        response = self.clients.ec2.describe_vpcs(
            Filters=[{"Name": "is-default", "Values": ["true"]}],
        )
        vpcs = response.get("Vpcs", [])
        if not vpcs:
            raise ValueError("No default VPC found. Configure VPC/subnet support before creating public RDS.")
        return vpcs[0]["VpcId"]

    def _wait_for_glue_database(self) -> None:
        for _attempt in range(12):
            try:
                self.clients.glue.get_database(Name=self.settings.glue_database)
                return
            except self.clients.glue.exceptions.EntityNotFoundException:
                self._sleep(5)
        raise TimeoutError(f"Glue database {self.settings.glue_database} was not available in time.")

    def _wait_for_athena_workgroup(self) -> None:
        for _attempt in range(12):
            try:
                self.clients.athena.get_work_group(WorkGroup=self.settings.athena_workgroup)
                return
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code not in {"InvalidRequestException", "ResourceNotFoundException"}:
                    raise
                self._sleep(5)
        raise TimeoutError(f"Athena workgroup {self.settings.athena_workgroup} was not available in time.")

    def _wait_for_mariadb_available(self) -> None:
        self.clients.rds.get_waiter("db_instance_available").wait(
            DBInstanceIdentifier=self.settings.rds_instance_identifier,
            WaiterConfig={"Delay": 30, "MaxAttempts": 80},
        )

    @staticmethod
    def _sleep(seconds: int) -> None:
        import time

        time.sleep(seconds)
