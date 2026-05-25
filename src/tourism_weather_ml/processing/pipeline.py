from tourism_weather_ml.aws.clients import AwsClients
from tourism_weather_ml.config import Settings


class ProcessingPipeline:
    def __init__(self, settings: Settings, clients: AwsClients) -> None:
        self.settings = settings
        self.clients = clients

    def run(self, dry_run: bool = True) -> list[str]:
        bucket = self.settings.s3_bucket_name or "<S3_BUCKET_NAME>"
        actions = [
            f"catalog bronze datasets from s3://{bucket}/{self.settings.s3_bronze_prefix}/ with Glue crawlers",
            (
                f"normalize Dataestur original files from "
                f"s3://{bucket}/{self.settings.s3_bronze_prefix}/dataestur/original/ "
                f"into s3://{bucket}/{self.settings.s3_silver_prefix}/dataestur/"
            ),
            "normalize tourism, weather, holidays and mobility to silver parquet tables",
            "aggregate weather by province/month",
            "join tourism demand with climate, calendar and mobility features",
            "write gold table tourism_weather_monthly_features",
            "make Athena table available for EDA and training",
            "optionally sync curated gold table to RDS MariaDB",
        ]
        return [f"DRY-RUN {action}" if dry_run else action for action in actions]
