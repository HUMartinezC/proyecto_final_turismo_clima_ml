from dataclasses import dataclass
import os
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from tourism_weather_ml.config import Settings


@dataclass(frozen=True)
class AwsClients:
    """Centralized boto3 client factory.

    Keeping clients here avoids scattering region/profile/session setup across
    ingestion, ETL and deployment code.
    """

    settings: Settings

    def session(self) -> boto3.Session:
        kwargs: dict[str, str] = {"region_name": self.settings.aws_region}
        has_env_credentials = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
        if self.settings.aws_profile and not has_env_credentials:
            kwargs["profile_name"] = self.settings.aws_profile
        return boto3.Session(**kwargs)

    def client(self, service_name: str, endpoint_url: Optional[str] = None) -> BaseClient:
        return self.session().client(
            service_name,
            endpoint_url=endpoint_url,
            config=Config(retries={"max_attempts": 10, "mode": "standard"}),
        )

    def resource(self, service_name: str):
        return self.session().resource(service_name)

    @property
    def s3(self) -> BaseClient:
        return self.client("s3")

    @property
    def sts(self) -> BaseClient:
        return self.client("sts")

    @property
    def glue(self) -> BaseClient:
        return self.client("glue")

    @property
    def athena(self) -> BaseClient:
        return self.client("athena")

    @property
    def lambda_(self) -> BaseClient:
        return self.client("lambda")

    @property
    def rds(self) -> BaseClient:
        return self.client("rds")

    @property
    def ec2(self) -> BaseClient:
        return self.client("ec2")

    @property
    def kafka(self) -> BaseClient:
        return self.client("kafka")

    @property
    def docdb(self) -> BaseClient:
        return self.client("docdb")
