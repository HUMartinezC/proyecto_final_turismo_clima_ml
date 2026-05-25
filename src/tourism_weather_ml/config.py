import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    return value if value != "" else None


def _parse_named_urls(value: Optional[str]) -> dict[str, str]:
    if not value:
        return {}
    urls: dict[str, str] = {}
    for item in value.split(";"):
        if not item.strip() or "=" not in item:
            continue
        name, url = item.split("=", 1)
        urls[name.strip()] = url.strip()
    return urls


def _parse_csv(value: Optional[str]) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().strip("/") for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables or .env."""

    project_name: str = "tourism-weather-ml"
    environment: str = "dev"
    aws_region: str = "eu-west-1"
    aws_profile: Optional[str] = "default"

    s3_bucket_name: Optional[str] = None
    s3_bronze_prefix: str = "bronze"
    s3_silver_prefix: str = "silver"
    s3_gold_prefix: str = "gold"

    glue_database: str = "tourism_weather_dev"
    athena_workgroup: str = "primary"
    athena_results_s3_uri: Optional[str] = None

    rds_host: Optional[str] = None
    rds_port: int = 3306
    rds_database: str = "tourism_weather"
    rds_user: Optional[str] = None
    rds_password: Optional[str] = None
    rds_engine: str = "mariadb"
    rds_instance_identifier: str = "tourism-weather-mariadb-dev"
    rds_instance_class: str = "db.t3.micro"
    rds_allocated_storage: int = 20
    rds_publicly_accessible: bool = True
    rds_security_group_name: str = "tourism-weather-mariadb-public"

    docdb_uri: Optional[str] = None
    docdb_database: str = "tourism_weather"

    kafka_bootstrap_servers: Optional[str] = None
    kafka_topic_weather: str = "weather_observations"
    kafka_topic_tourism: str = "tourism_events"

    aemet_api_key: Optional[str] = None
    dataestur_base_url: str = "https://dataestur.azure-api.net/API-SEGITTUR-v1/"
    dataestur_endpoints: tuple[str, ...] = ()
    dataestur_from_year: Optional[int] = None
    dataestur_from_month: Optional[int] = None
    dataestur_to_year: Optional[int] = None
    dataestur_to_month: Optional[int] = None
    dataestur_eoh_request_url: Optional[str] = None
    dataestur_extra_request_urls: Optional[str] = None
    aena_base_url: Optional[str] = None

    lambda_function_name: str = "tourism-weather-ingestion"
    lambda_role_arn: Optional[str] = None

    @property
    def dataestur_request_urls(self) -> dict[str, str]:
        urls = _parse_named_urls(self.dataestur_extra_request_urls)
        if self.dataestur_eoh_request_url:
            urls.setdefault("hotel_occupancy_eoh", self.dataestur_eoh_request_url)
        return urls

    @property
    def required_aws_values(self) -> list[str]:
        required = []
        if not self.s3_bucket_name:
            required.append("S3_BUCKET_NAME")
        if not self.athena_results_s3_uri:
            required.append("ATHENA_RESULTS_S3_URI")
        return required


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        project_name=_env("PROJECT_NAME", "tourism-weather-ml") or "tourism-weather-ml",
        environment=_env("ENVIRONMENT", "dev") or "dev",
        aws_region=_env("AWS_REGION", "eu-west-1") or "eu-west-1",
        aws_profile=_env("AWS_PROFILE", "default"),
        s3_bucket_name=_env("S3_BUCKET_NAME"),
        s3_bronze_prefix=_env("S3_BRONZE_PREFIX", "bronze") or "bronze",
        s3_silver_prefix=_env("S3_SILVER_PREFIX", "silver") or "silver",
        s3_gold_prefix=_env("S3_GOLD_PREFIX", "gold") or "gold",
        glue_database=_env("GLUE_DATABASE", "tourism_weather_dev") or "tourism_weather_dev",
        athena_workgroup=_env("ATHENA_WORKGROUP", "primary") or "primary",
        athena_results_s3_uri=_env("ATHENA_RESULTS_S3_URI"),
        rds_host=_env("RDS_HOST"),
        rds_port=int(_env("RDS_PORT", "3306") or "3306"),
        rds_database=_env("RDS_DATABASE", "tourism_weather") or "tourism_weather",
        rds_user=_env("RDS_USER"),
        rds_password=_env("RDS_PASSWORD"),
        rds_engine=_env("RDS_ENGINE", "mariadb") or "mariadb",
        rds_instance_identifier=_env(
            "RDS_INSTANCE_IDENTIFIER",
            "tourism-weather-mariadb-dev",
        )
        or "tourism-weather-mariadb-dev",
        rds_instance_class=_env("RDS_INSTANCE_CLASS", "db.t3.micro") or "db.t3.micro",
        rds_allocated_storage=int(_env("RDS_ALLOCATED_STORAGE", "20") or "20"),
        rds_publicly_accessible=(_env("RDS_PUBLICLY_ACCESSIBLE", "true") or "true").lower()
        == "true",
        rds_security_group_name=_env(
            "RDS_SECURITY_GROUP_NAME",
            "tourism-weather-mariadb-public",
        )
        or "tourism-weather-mariadb-public",
        docdb_uri=_env("DOCDB_URI"),
        docdb_database=_env("DOCDB_DATABASE", "tourism_weather") or "tourism_weather",
        kafka_bootstrap_servers=_env("KAFKA_BOOTSTRAP_SERVERS"),
        kafka_topic_weather=_env("KAFKA_TOPIC_WEATHER", "weather_observations")
        or "weather_observations",
        kafka_topic_tourism=_env("KAFKA_TOPIC_TOURISM", "tourism_events") or "tourism_events",
        aemet_api_key=_env("AEMET_API_KEY"),
        dataestur_base_url=_env(
            "DATAESTUR_BASE_URL",
            "https://dataestur.azure-api.net/API-SEGITTUR-v1/",
        )
        or "https://dataestur.azure-api.net/API-SEGITTUR-v1/",
        dataestur_endpoints=_parse_csv(_env("DATAESTUR_ENDPOINTS")),
        dataestur_from_year=int(_env("DATAESTUR_FROM_YEAR")) if _env("DATAESTUR_FROM_YEAR") else None,
        dataestur_from_month=int(_env("DATAESTUR_FROM_MONTH"))
        if _env("DATAESTUR_FROM_MONTH")
        else None,
        dataestur_to_year=int(_env("DATAESTUR_TO_YEAR")) if _env("DATAESTUR_TO_YEAR") else None,
        dataestur_to_month=int(_env("DATAESTUR_TO_MONTH")) if _env("DATAESTUR_TO_MONTH") else None,
        dataestur_eoh_request_url=_env("DATAESTUR_EOH_REQUEST_URL"),
        dataestur_extra_request_urls=_env("DATAESTUR_EXTRA_REQUEST_URLS"),
        aena_base_url=_env("AENA_BASE_URL"),
        lambda_function_name=_env("LAMBDA_FUNCTION_NAME", "tourism-weather-ingestion")
        or "tourism-weather-ingestion",
        lambda_role_arn=_env("LAMBDA_ROLE_ARN"),
    )
