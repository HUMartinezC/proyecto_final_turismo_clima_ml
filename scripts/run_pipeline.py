#!/usr/bin/env python
"""Single-file data platform runner.

This script is intentionally self-contained for the course deliverable: it can
deploy the minimal AWS architecture, ingest the selected public sources and
process local raw files without importing project modules from ``src``.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "datasets" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "datasets" / "processed"
LOGGER = logging.getLogger("run_pipeline")
SKIP_S3_UPLOAD = False


ATHENA_QUERY_POLL_SECONDS = 2
ATHENA_QUERY_TIMEOUT_SECONDS = 120


PARQUET_STRING_COLUMNS = {
    "airport_name",
    "airport_normalized",
    "ccaa",
    "country",
    "date",
    "feature_source",
    "file_name",
    "holiday_name",
    "local_path",
    "modified_at",
    "province",
    "region_code",
    "region_name",
    "scope",
    "source",
    "source_file",
    "source_sheet",
    "suffix",
    "year_month",
}


DATAESTUR_ENDPOINTS = {
    "EOH_PROV_DL": "hotel_occupancy_by_province",
    "EOH_CCAA_DL": "hotel_occupancy_by_region",
    "FRONTUR_DL": "international_arrivals",
    "ETR_DL": "resident_tourism",
    "EGATUR_DL": "international_tourist_spending",
    "AENA_DESTINOS_DL": "air_traffic",
    "VALORES_CLIMATOLOGICOS_TEMPERATURA_DL": "climate_temperature",
    "VALORES_CLIMATOLOGICOS_PRECIPITACION_DL": "climate_precipitation",
}


@dataclass(frozen=True)
class WeatherLocation:
    code: str
    province: str
    latitude: float
    longitude: float


WEATHER_LOCATIONS = (
    WeatherLocation("alava", "Alava", 42.8467, -2.6727),
    WeatherLocation("albacete", "Albacete", 38.9942, -1.8564),
    WeatherLocation("alicante", "Alicante", 38.3452, -0.4810),
    WeatherLocation("almeria", "Almeria", 36.8340, -2.4637),
    WeatherLocation("asturias", "Asturias", 43.3614, -5.8593),
    WeatherLocation("avila", "Avila", 40.6565, -4.6818),
    WeatherLocation("badajoz", "Badajoz", 38.8794, -6.9707),
    WeatherLocation("barcelona", "Barcelona", 41.3874, 2.1686),
    WeatherLocation("burgos", "Burgos", 42.3439, -3.6969),
    WeatherLocation("caceres", "Caceres", 39.4753, -6.3724),
    WeatherLocation("cadiz", "Cadiz", 36.5271, -6.2886),
    WeatherLocation("cantabria", "Cantabria", 43.4623, -3.8099),
    WeatherLocation("castellon", "Castellon", 39.9864, -0.0513),
    WeatherLocation("ceuta", "Ceuta", 35.8894, -5.3213),
    WeatherLocation("ciudad_real", "Ciudad Real", 38.9848, -3.9274),
    WeatherLocation("cordoba", "Cordoba", 37.8882, -4.7794),
    WeatherLocation("cuenca", "Cuenca", 40.0704, -2.1374),
    WeatherLocation("girona", "Girona", 41.9794, 2.8214),
    WeatherLocation("granada", "Granada", 37.1773, -3.5986),
    WeatherLocation("guadalajara", "Guadalajara", 40.6330, -3.1661),
    WeatherLocation("gipuzkoa", "Gipuzkoa", 43.3183, -1.9812),
    WeatherLocation("huelva", "Huelva", 37.2614, -6.9447),
    WeatherLocation("huesca", "Huesca", 42.1401, -0.4089),
    WeatherLocation("illes_balears", "Illes Balears", 39.5696, 2.6502),
    WeatherLocation("jaen", "Jaen", 37.7796, -3.7849),
    WeatherLocation("a_coruna", "A Coruna", 43.3623, -8.4115),
    WeatherLocation("la_rioja", "La Rioja", 42.4627, -2.4449),
    WeatherLocation("las_palmas", "Las Palmas", 28.1235, -15.4363),
    WeatherLocation("leon", "Leon", 42.5987, -5.5671),
    WeatherLocation("lleida", "Lleida", 41.6176, 0.6200),
    WeatherLocation("lugo", "Lugo", 43.0097, -7.5568),
    WeatherLocation("madrid", "Madrid", 40.4168, -3.7038),
    WeatherLocation("malaga", "Malaga", 36.7213, -4.4214),
    WeatherLocation("melilla", "Melilla", 35.2923, -2.9381),
    WeatherLocation("murcia", "Murcia", 37.9922, -1.1307),
    WeatherLocation("navarra", "Navarra", 42.8125, -1.6458),
    WeatherLocation("ourense", "Ourense", 42.3358, -7.8639),
    WeatherLocation("palencia", "Palencia", 42.0097, -4.5288),
    WeatherLocation("pontevedra", "Pontevedra", 42.4310, -8.6444),
    WeatherLocation("salamanca", "Salamanca", 40.9701, -5.6635),
    WeatherLocation("santa_cruz_tenerife", "Santa Cruz de Tenerife", 28.4636, -16.2518),
    WeatherLocation("segovia", "Segovia", 40.9429, -4.1088),
    WeatherLocation("sevilla", "Sevilla", 37.3891, -5.9845),
    WeatherLocation("soria", "Soria", 41.7666, -2.4790),
    WeatherLocation("tarragona", "Tarragona", 41.1189, 1.2445),
    WeatherLocation("teruel", "Teruel", 40.3456, -1.1065),
    WeatherLocation("toledo", "Toledo", 39.8628, -4.0273),
    WeatherLocation("valencia", "Valencia", 39.4699, -0.3763),
    WeatherLocation("valladolid", "Valladolid", 41.6523, -4.7245),
    WeatherLocation("bizkaia", "Bizkaia", 43.2630, -2.9350),
    WeatherLocation("zamora", "Zamora", 41.5035, -5.7446),
    WeatherLocation("zaragoza", "Zaragoza", 41.6488, -0.8891),
)


DAILY_WEATHER_VARS = (
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
)


SPANISH_REGION_SUBDIVISIONS = {
    "AN": "Andalucia",
    "AR": "Aragon",
    "AS": "Asturias",
    "CB": "Cantabria",
    "CE": "Ceuta",
    "CL": "Castilla y Leon",
    "CM": "Castilla-La Mancha",
    "CN": "Canarias",
    "CT": "Cataluna",
    "EX": "Extremadura",
    "GA": "Galicia",
    "IB": "Illes Balears",
    "MC": "Murcia",
    "MD": "Madrid",
    "ML": "Melilla",
    "NC": "Navarra",
    "PV": "Pais Vasco",
    "RI": "La Rioja",
    "VC": "Comunitat Valenciana",
}


PROVINCE_REGION_CODES = {
    "Alava": "PV",
    "Albacete": "CM",
    "Alicante": "VC",
    "Almeria": "AN",
    "Asturias": "AS",
    "Avila": "CL",
    "Badajoz": "EX",
    "Barcelona": "CT",
    "Burgos": "CL",
    "Caceres": "EX",
    "Cadiz": "AN",
    "Cantabria": "CB",
    "Castellon": "VC",
    "Ceuta": "CE",
    "Ciudad Real": "CM",
    "Cordoba": "AN",
    "Cuenca": "CM",
    "Girona": "CT",
    "Granada": "AN",
    "Guadalajara": "CM",
    "Gipuzkoa": "PV",
    "Huelva": "AN",
    "Huesca": "AR",
    "Illes Balears": "IB",
    "Jaen": "AN",
    "A Coruna": "GA",
    "La Rioja": "RI",
    "Las Palmas": "CN",
    "Leon": "CL",
    "Lleida": "CT",
    "Lugo": "GA",
    "Madrid": "MD",
    "Malaga": "AN",
    "Melilla": "ML",
    "Murcia": "MC",
    "Navarra": "NC",
    "Ourense": "GA",
    "Palencia": "CL",
    "Pontevedra": "GA",
    "Salamanca": "CL",
    "Santa Cruz de Tenerife": "CN",
    "Segovia": "CL",
    "Sevilla": "AN",
    "Soria": "CL",
    "Tarragona": "CT",
    "Teruel": "AR",
    "Toledo": "CM",
    "Valencia": "VC",
    "Valladolid": "CL",
    "Bizkaia": "PV",
    "Zamora": "CL",
    "Zaragoza": "AR",
}


DATAESTUR_PROVINCE_ALIASES = {
    "ALAVA": "Alava",
    "ALMERIA": "Almeria",
    "AVILA": "Avila",
    "CACERES": "Caceres",
    "CADIZ": "Cadiz",
    "CASTELLON": "Castellon",
    "CORDOBA": "Cordoba",
    "GERONA": "Girona",
    "GUIPUZCOA": "Gipuzkoa",
    "ISLAS BALEARES": "Illes Balears",
    "JAEN": "Jaen",
    "LA CORUNA": "A Coruna",
    "LEON": "Leon",
    "LERIDA": "Lleida",
    "MALAGA": "Malaga",
    "ORENSE": "Ourense",
    "VIZCAYA": "Bizkaia",
}


AENA_AIRPORT_PROVINCES = {
    "A CORUNA": "A Coruna",
    "ADOLFO SUAREZ MADRID-BARAJAS": "Madrid",
    "AEROPUERTO INTL. REGION MURCIA": "Murcia",
    "ALBACETE": "Albacete",
    "ALGECIRAS-HELIPUERTO": "Cadiz",
    "ALICANTE-ELCHE": "Alicante",
    "ALICANTE-ELCHE MIGUEL HDEZ.": "Alicante",
    "ALMERIA": "Almeria",
    "ASTURIAS": "Asturias",
    "BADAJOZ": "Badajoz",
    "BARCELONA-EL PRAT": "Barcelona",
    "BARCELONA-EL PRAT J.T.": "Barcelona",
    "BILBAO": "Bizkaia",
    "BURGOS": "Burgos",
    "CEUTA-HELIPUERTO": "Ceuta",
    "CORDOBA": "Cordoba",
    "EL HIERRO": "Santa Cruz de Tenerife",
    "FGL GRANADA-JAEN": "Granada",
    "FUERTEVENTURA": "Las Palmas",
    "GIRONA": "Girona",
    "GIRONA-COSTA BRAVA": "Girona",
    "GRAN CANARIA": "Las Palmas",
    "HUESCA-PIRINEOS": "Huesca",
    "IBIZA": "Illes Balears",
    "JEREZ DE LA FRONTERA": "Cadiz",
    "LA GOMERA": "Santa Cruz de Tenerife",
    "LA PALMA": "Santa Cruz de Tenerife",
    "LANZAROTE": "Las Palmas",
    "LANZAROTE CESAR MANRIQUE": "Las Palmas",
    "LANZAROTE-CESAR MANRIQUE": "Las Palmas",
    "LEON": "Leon",
    "LOGRONO": "La Rioja",
    "MADRID-CUATRO VIENTOS": "Madrid",
    "MALAGA-COSTA DEL SOL": "Malaga",
    "MELILLA": "Melilla",
    "MENORCA": "Illes Balears",
    "MURCIA-SAN JAVIER": "Murcia",
    "PALMA DE MALLORCA": "Illes Balears",
    "PAMPLONA": "Navarra",
    "REUS": "Tarragona",
    "SABADELL": "Barcelona",
    "SALAMANCA": "Salamanca",
    "SAN SEBASTIAN": "Gipuzkoa",
    "SANTIAGO": "A Coruna",
    "SANTIAGO-ROSALIA DE CASTRO": "A Coruna",
    "SEVE BALLESTEROS-SANTANDER": "Cantabria",
    "SEVILLA": "Sevilla",
    "SON BONET": "Illes Balears",
    "TENERIFE NORTE": "Santa Cruz de Tenerife",
    "TENERIFE NORTE-C. LA LAGUNA": "Santa Cruz de Tenerife",
    "TENERIFE SUR": "Santa Cruz de Tenerife",
    "TENERIFE-NORTE": "Santa Cruz de Tenerife",
    "TENERIFE-SUR": "Santa Cruz de Tenerife",
    "VALENCIA": "Valencia",
    "VALLADOLID": "Valladolid",
    "VIGO": "Pontevedra",
    "VITORIA": "Alava",
    "ZARAGOZA": "Zaragoza",
}


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in {"", None} else None


def parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().strip("/") for item in value.split(",") if item.strip())


def parse_named_urls(value: str | None) -> dict[str, str]:
    urls: dict[str, str] = {}
    if not value:
        return urls
    for item in value.split(";"):
        if "=" not in item:
            continue
        name, url = item.split("=", 1)
        if name.strip() and url.strip():
            urls[name.strip()] = url.strip()
    return urls


@dataclass(frozen=True)
class Settings:
    project_name: str
    environment: str
    aws_region: str
    aws_profile: str | None
    s3_bucket_name: str | None
    s3_bronze_prefix: str
    s3_silver_prefix: str
    s3_gold_prefix: str
    glue_database: str
    athena_workgroup: str
    athena_results_s3_uri: str | None
    rds_instance_identifier: str
    rds_instance_class: str
    rds_allocated_storage: int
    rds_publicly_accessible: bool
    rds_security_group_name: str
    rds_database: str
    rds_user: str | None
    rds_password: str | None
    rds_port: int
    docdb_uri: str | None
    kafka_bootstrap_servers: str | None
    lambda_function_name: str
    lambda_role_arn: str | None
    dataestur_base_url: str
    dataestur_endpoints: tuple[str, ...]
    dataestur_from_year: int | None
    dataestur_from_month: int | None
    dataestur_to_year: int | None
    dataestur_to_month: int | None
    dataestur_eoh_request_url: str | None
    dataestur_extra_request_urls: str | None
    open_meteo_base_url: str
    open_meteo_from_date: str
    open_meteo_to_date: str
    open_meteo_locations: tuple[str, ...]
    open_meteo_timezone: str
    open_meteo_min_seconds_between_requests: float
    open_meteo_retry_attempts: int
    open_meteo_retry_base_seconds: float
    open_meteo_skip_existing: bool
    holidays_from_year: int
    holidays_to_year: int

    @property
    def required_aws_values(self) -> list[str]:
        missing = []
        if not self.s3_bucket_name:
            missing.append("S3_BUCKET_NAME")
        if not self.athena_results_s3_uri:
            missing.append("ATHENA_RESULTS_S3_URI")
        return missing

    @property
    def dataestur_request_urls(self) -> dict[str, str]:
        urls = parse_named_urls(self.dataestur_extra_request_urls)
        if self.dataestur_eoh_request_url:
            urls.setdefault("hotel_occupancy_eoh", self.dataestur_eoh_request_url)
        return urls


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        project_name=env("PROJECT_NAME", "tourism-weather-ml") or "tourism-weather-ml",
        environment=env("ENVIRONMENT", "dev") or "dev",
        aws_region=env("AWS_REGION", "eu-west-1") or "eu-west-1",
        aws_profile=env("AWS_PROFILE", "default"),
        s3_bucket_name=env("S3_BUCKET_NAME"),
        s3_bronze_prefix=env("S3_BRONZE_PREFIX", "bronze") or "bronze",
        s3_silver_prefix=env("S3_SILVER_PREFIX", "silver") or "silver",
        s3_gold_prefix=env("S3_GOLD_PREFIX", "gold") or "gold",
        glue_database=env("GLUE_DATABASE", "tourism_weather_dev") or "tourism_weather_dev",
        athena_workgroup=env("ATHENA_WORKGROUP", "primary") or "primary",
        athena_results_s3_uri=env("ATHENA_RESULTS_S3_URI"),
        rds_instance_identifier=env("RDS_INSTANCE_IDENTIFIER", "tourism-weather-mariadb-dev")
        or "tourism-weather-mariadb-dev",
        rds_instance_class=env("RDS_INSTANCE_CLASS", "db.t3.micro") or "db.t3.micro",
        rds_allocated_storage=int(env("RDS_ALLOCATED_STORAGE", "20") or "20"),
        rds_publicly_accessible=(env("RDS_PUBLICLY_ACCESSIBLE", "true") or "true").lower()
        == "true",
        rds_security_group_name=env("RDS_SECURITY_GROUP_NAME", "tourism-weather-mariadb-public")
        or "tourism-weather-mariadb-public",
        rds_database=env("RDS_DATABASE", "tourism_weather") or "tourism_weather",
        rds_user=env("RDS_USER"),
        rds_password=env("RDS_PASSWORD"),
        rds_port=int(env("RDS_PORT", "3306") or "3306"),
        docdb_uri=env("DOCDB_URI"),
        kafka_bootstrap_servers=env("KAFKA_BOOTSTRAP_SERVERS"),
        lambda_function_name=env("LAMBDA_FUNCTION_NAME", "tourism-weather-ingestion")
        or "tourism-weather-ingestion",
        lambda_role_arn=env("LAMBDA_ROLE_ARN"),
        dataestur_base_url=env(
            "DATAESTUR_BASE_URL",
            "https://dataestur.azure-api.net/API-SEGITTUR-v1/",
        )
        or "https://dataestur.azure-api.net/API-SEGITTUR-v1/",
        dataestur_endpoints=parse_csv(env("DATAESTUR_ENDPOINTS"))
        or tuple(DATAESTUR_ENDPOINTS.keys()),
        dataestur_from_year=int(env("DATAESTUR_FROM_YEAR")) if env("DATAESTUR_FROM_YEAR") else None,
        dataestur_from_month=int(env("DATAESTUR_FROM_MONTH")) if env("DATAESTUR_FROM_MONTH") else None,
        dataestur_to_year=int(env("DATAESTUR_TO_YEAR")) if env("DATAESTUR_TO_YEAR") else None,
        dataestur_to_month=int(env("DATAESTUR_TO_MONTH")) if env("DATAESTUR_TO_MONTH") else None,
        dataestur_eoh_request_url=env("DATAESTUR_EOH_REQUEST_URL"),
        dataestur_extra_request_urls=env("DATAESTUR_EXTRA_REQUEST_URLS"),
        open_meteo_base_url=env(
            "OPEN_METEO_BASE_URL",
            "https://archive-api.open-meteo.com/v1/archive",
        )
        or "https://archive-api.open-meteo.com/v1/archive",
        open_meteo_from_date=(env("OPEN_METEO_FROM_DATE") or "2015-10-01").split("T", 1)[0],
        open_meteo_to_date=(env("OPEN_METEO_TO_DATE") or "2024-12-31").split("T", 1)[0],
        open_meteo_locations=parse_csv(env("OPEN_METEO_LOCATIONS")),
        open_meteo_timezone=env("OPEN_METEO_TIMEZONE", "Europe/Madrid") or "Europe/Madrid",
        open_meteo_min_seconds_between_requests=float(env("OPEN_METEO_MIN_SECONDS_BETWEEN_REQUESTS", "5") or "5"),
        open_meteo_retry_attempts=int(env("OPEN_METEO_RETRY_ATTEMPTS", "6") or "6"),
        open_meteo_retry_base_seconds=float(env("OPEN_METEO_RETRY_BASE_SECONDS", "10") or "10"),
        open_meteo_skip_existing=(env("OPEN_METEO_SKIP_EXISTING", "true") or "true").lower()
        == "true",
        holidays_from_year=int(
            env("HOLIDAYS_FROM_YEAR", (env("OPEN_METEO_FROM_DATE") or "2015-10-01")[:4])
            or "2015"
        ),
        holidays_to_year=int(
            env("HOLIDAYS_TO_YEAR", (env("OPEN_METEO_TO_DATE") or "2024-12-31")[:4])
            or "2024"
        ),
    )


def boto3_session(settings: Settings):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc

    kwargs: dict[str, str] = {"region_name": settings.aws_region}
    has_env_credentials = bool(env("AWS_ACCESS_KEY_ID") and env("AWS_SECRET_ACCESS_KEY"))
    if settings.aws_profile and not has_env_credentials:
        kwargs["profile_name"] = settings.aws_profile
    return boto3.Session(**kwargs)


def aws_client(settings: Settings, service: str):
    return boto3_session(settings).client(service)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-script deploy, ingestion and processing pipeline."
    )
    parser.add_argument("--deploy", action="store_true", help="Provision AWS resources.")
    parser.add_argument("--ingest", action="store_true", help="Ingest selected data sources.")
    parser.add_argument("--process", action="store_true", help="Process and unify datasets.")
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Create/update Athena external tables in the Glue Data Catalog for silver/gold Parquet outputs.",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip source ingestion/downloads when running the default deploy+ingest+process flow.",
    )
    parser.add_argument(
        "--source",
        choices=("dataestur", "open_meteo", "aemet", "holidays", "aena"),
        help="Limit ingestion or processing to one source.",
    )
    parser.add_argument("--list-dataestur", action="store_true", help="List Dataestur endpoints.")
    parser.add_argument("--check-config", action="store_true", help="Print non-secret config checks.")
    parser.add_argument("--dataestur-endpoint", action="append", help="Limit Dataestur endpoint.")
    parser.add_argument("--dataestur-limit", type=int, help="Limit Dataestur downloads.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue after source errors.")
    parser.add_argument("--dry-run", action="store_true", help="Plan actions without writes or downloads.")
    parser.add_argument(
        "--skip-s3-upload",
        action="store_true",
        help="Write local raw/silver/gold files without uploading them to S3.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Control output verbosity.",
    )
    return parser.parse_args()


def print_config_check(settings: Settings) -> None:
    checks = {
        "AWS_REGION": settings.aws_region,
        "AWS_PROFILE": settings.aws_profile or "<env/default credential chain>",
        "S3_BUCKET_NAME": "configured" if settings.s3_bucket_name else "missing",
        "ATHENA_RESULTS_S3_URI": "configured" if settings.athena_results_s3_uri else "missing",
        "GLUE_DATABASE": settings.glue_database,
        "RDS_INSTANCE_IDENTIFIER": settings.rds_instance_identifier,
        "RDS_USER": "configured" if settings.rds_user else "missing",
        "RDS_PASSWORD": "configured" if settings.rds_password else "missing",
        "DOCDB_URI": "configured" if settings.docdb_uri else "missing",
        "KAFKA_BOOTSTRAP_SERVERS": "configured" if settings.kafka_bootstrap_servers else "missing",
        "LAMBDA_ROLE_ARN": "configured" if settings.lambda_role_arn else "missing",
        "OPEN_METEO_RANGE": f"{settings.open_meteo_from_date} to {settings.open_meteo_to_date}",
        "OPEN_METEO_LOCATIONS": ", ".join(settings.open_meteo_locations) or "all province capitals",
        "HOLIDAYS_RANGE": f"{settings.holidays_from_year} to {settings.holidays_to_year}",
        "DATAESTUR_ENDPOINTS": ", ".join(settings.dataestur_endpoints),
    }
    for key, value in checks.items():
        print(f"- {key}: {value}")


def provision(settings: Settings, dry_run: bool) -> list[str]:
    actions = [
        "validate AWS identity with STS",
        f"ensure S3 bucket and lake prefixes: {settings.s3_bucket_name}",
        f"ensure Glue database: {settings.glue_database}",
        f"ensure Athena workgroup: {settings.athena_workgroup}",
        f"ensure RDS MariaDB instance: {settings.rds_instance_identifier}",
        f"prepare Lambda function when LAMBDA_ROLE_ARN is configured: {settings.lambda_function_name}",
        "validate DocumentDB and Kafka configuration when provided",
    ]
    if dry_run:
        return [f"DRY-RUN {action}" for action in actions]

    aws_client(settings, "sts").get_caller_identity()
    ensure_bucket(settings)
    ensure_glue_database(settings)
    ensure_athena_workgroup(settings)
    ensure_rds_instance(settings)
    ensure_lambda_function(settings)
    return actions


def ensure_bucket(settings: Settings) -> None:
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is required.")
    s3 = aws_client(settings, "s3")
    try:
        s3.head_bucket(Bucket=settings.s3_bucket_name)
    except Exception:
        create_args: dict[str, Any] = {"Bucket": settings.s3_bucket_name}
        if settings.aws_region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {"LocationConstraint": settings.aws_region}
        s3.create_bucket(**create_args)
        s3.get_waiter("bucket_exists").wait(Bucket=settings.s3_bucket_name)
    for prefix in (settings.s3_bronze_prefix, settings.s3_silver_prefix, settings.s3_gold_prefix):
        s3.put_object(Bucket=settings.s3_bucket_name, Key=f"{prefix}/")


def ensure_glue_database(settings: Settings) -> None:
    glue = aws_client(settings, "glue")
    try:
        glue.get_database(Name=settings.glue_database)
    except Exception:
        glue.create_database(DatabaseInput={"Name": settings.glue_database})


def ensure_athena_workgroup(settings: Settings) -> None:
    if not settings.athena_results_s3_uri:
        raise ValueError("ATHENA_RESULTS_S3_URI is required.")
    athena = aws_client(settings, "athena")
    try:
        athena.get_work_group(WorkGroup=settings.athena_workgroup)
    except Exception:
        athena.create_work_group(
            Name=settings.athena_workgroup,
            Configuration={"ResultConfiguration": {"OutputLocation": settings.athena_results_s3_uri}},
            Description="Tourism-weather ML workgroup",
        )


def ensure_rds_instance(settings: Settings) -> None:
    if not settings.rds_user or not settings.rds_password:
        LOGGER.warning("Skipping RDS creation because RDS_USER/RDS_PASSWORD are missing.")
        return
    rds = aws_client(settings, "rds")
    try:
        rds.describe_db_instances(DBInstanceIdentifier=settings.rds_instance_identifier)
        return
    except Exception:
        pass
    rds.create_db_instance(
        DBInstanceIdentifier=settings.rds_instance_identifier,
        DBInstanceClass=settings.rds_instance_class,
        Engine="mariadb",
        AllocatedStorage=settings.rds_allocated_storage,
        DBName=settings.rds_database,
        MasterUsername=settings.rds_user,
        MasterUserPassword=settings.rds_password,
        Port=settings.rds_port,
        PubliclyAccessible=settings.rds_publicly_accessible,
        BackupRetentionPeriod=0,
        DeletionProtection=False,
    )


def ensure_lambda_function(settings: Settings) -> None:
    if not settings.lambda_role_arn:
        LOGGER.warning("Skipping Lambda creation because LAMBDA_ROLE_ARN is missing.")
        return
    lambda_client = aws_client(settings, "lambda")
    code = (
        "def handler(event, context):\n"
        "    return {'statusCode': 200, 'body': 'tourism-weather ingestion placeholder'}\n"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("lambda_function.py", code)
    try:
        lambda_client.get_function(FunctionName=settings.lambda_function_name)
        lambda_client.update_function_code(
            FunctionName=settings.lambda_function_name,
            ZipFile=buffer.getvalue(),
        )
    except Exception:
        lambda_client.create_function(
            FunctionName=settings.lambda_function_name,
            Runtime="python3.11",
            Role=settings.lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": buffer.getvalue()},
            Description="Course project ingestion automation placeholder",
        )


def ingest(settings: Settings, args: argparse.Namespace) -> list[str]:
    actions: list[str] = []
    selected = (args.source,) if args.source else ("dataestur", "open_meteo", "holidays", "aena")
    for source in selected:
        try:
            if source == "dataestur":
                actions.extend(ingest_dataestur(settings, args))
            elif source == "open_meteo":
                actions.extend(ingest_open_meteo(settings, args.dry_run))
            elif source == "holidays":
                actions.extend(ingest_holidays(settings, args.dry_run))
            elif source == "aena":
                actions.extend(ingest_aena(settings, args.dry_run))
            elif source == "aemet":
                actions.append(
                    "skipped aemet: optional contrast source, not part of the default "
                    "single-file pipeline"
                )
            else:
                actions.append(f"skipped {source}: connector not implemented in this single-file MVP")
        except Exception as exc:
            LOGGER.error("%s ingestion failed: %s", source, exc)
            if not args.continue_on_error:
                raise
            actions.append(f"skipped {source} after error: {exc}")
    return actions


def ingest_aena(settings: Settings, dry_run: bool) -> list[str]:
    files = sorted((RAW_DIR / "aena").glob("*.xls")) + sorted((RAW_DIR / "aena").glob("*.xlsx"))
    if dry_run:
        return [f"DRY-RUN register {len(files)} local AENA Excel files from {RAW_DIR / 'aena'}"]
    for path in files:
        upload_to_s3(settings, path, f"{settings.s3_bronze_prefix}/aena/original/{path.name}")
    return [f"registered {len(files)} local AENA Excel files from {RAW_DIR / 'aena'}"]


def ingest_holidays(settings: Settings, dry_run: bool) -> list[str]:
    output_dir = RAW_DIR / "holidays" / "original"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"spanish_holidays_{settings.holidays_from_year}_{settings.holidays_to_year}.csv"
    metadata_path = csv_path.with_suffix(csv_path.suffix + ".metadata.json")
    if dry_run:
        return [f"DRY-RUN generate Spanish holidays calendar -> {csv_path}"]

    rows = build_holiday_rows(settings)
    write_csv(csv_path, rows)
    metadata_path.write_text(
        json.dumps(
            {
                "source": "python-holidays",
                "country": "ES",
                "from_year": settings.holidays_from_year,
                "to_year": settings.holidays_to_year,
                "regions": SPANISH_REGION_SUBDIVISIONS,
                "rows": len(rows),
                "generated_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                "local_path": str(csv_path),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    upload_to_s3(settings, csv_path, f"{settings.s3_bronze_prefix}/holidays/original/{csv_path.name}")
    upload_to_s3(
        settings,
        metadata_path,
        f"{settings.s3_bronze_prefix}/holidays/landing_manifest/{metadata_path.name}",
    )
    return [f"generated Spanish holidays calendar with {len(rows)} rows -> {csv_path}"]


def build_holiday_rows(settings: Settings) -> list[dict[str, Any]]:
    try:
        import holidays
    except ImportError as exc:
        raise RuntimeError("Install the holidays source with `pip install holidays pandas`.") from exc

    years = range(settings.holidays_from_year, settings.holidays_to_year + 1)
    national = holidays.country_holidays("ES", years=years, language="es")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for day, name in sorted(national.items()):
        key = (day.isoformat(), "ES", str(name), "national")
        seen.add(key)
        rows.append(
            {
                "date": day.isoformat(),
                "country": "ES",
                "region_code": "ES",
                "region_name": "España",
                "holiday_name": str(name),
                "scope": "national",
            }
        )

    for region_code, region_name in SPANISH_REGION_SUBDIVISIONS.items():
        regional = holidays.country_holidays("ES", subdiv=region_code, years=years, language="es")
        for day, name in sorted(regional.items()):
            if day in national and str(national[day]) == str(name):
                continue
            key = (day.isoformat(), region_code, str(name), "regional")
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "date": day.isoformat(),
                    "country": "ES",
                    "region_code": region_code,
                    "region_name": region_name,
                    "holiday_name": str(name),
                    "scope": "regional",
                }
            )

    return sorted(rows, key=lambda row: (row["date"], row["region_code"], row["holiday_name"]))


def ingest_dataestur(settings: Settings, args: argparse.Namespace) -> list[str]:
    sources = configured_dataestur_sources(settings, tuple(args.dataestur_endpoint or ()))
    if args.dataestur_limit is not None:
        sources = sources[: args.dataestur_limit]
    actions = []
    output_dir = RAW_DIR / "dataestur" / "original"
    manifest_dir = RAW_DIR / "dataestur" / "landing_manifest"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for index, (name, url) in enumerate(sources):
        if args.dry_run:
            actions.append(f"DRY-RUN ingest Dataestur {name}: GET {url} -> {output_dir}")
            continue
        if index:
            time.sleep(6.5)
        path, manifest_path = download_file(url, output_dir, safe_stem(name), "dataestur")
        upload_to_s3(settings, path, f"{settings.s3_bronze_prefix}/dataestur/original/{path.name}")
        upload_to_s3(settings, manifest_path, f"{settings.s3_bronze_prefix}/dataestur/landing_manifest/{manifest_path.name}")
        actions.append(f"downloaded Dataestur {name} to {path}")
    return actions


def configured_dataestur_sources(settings: Settings, endpoints: tuple[str, ...]) -> list[tuple[str, str]]:
    selected = endpoints or settings.dataestur_endpoints or tuple(DATAESTUR_ENDPOINTS.keys())
    sources = [
        (DATAESTUR_ENDPOINTS.get(endpoint, endpoint.lower().removesuffix("_dl")), build_dataestur_url(settings, endpoint))
        for endpoint in selected
    ]
    sources.extend(settings.dataestur_request_urls.items())
    return sources


def build_dataestur_url(settings: Settings, endpoint: str) -> str:
    base = settings.dataestur_base_url.rstrip("/") + "/"
    url = urljoin(base, endpoint.strip().strip("/"))
    params: dict[str, int] = {}
    if settings.dataestur_from_year:
        params["desde (año)"] = settings.dataestur_from_year
    if settings.dataestur_from_month:
        params["desde (mes)"] = settings.dataestur_from_month
    if settings.dataestur_to_year:
        params["hasta (año)"] = settings.dataestur_to_year
    if settings.dataestur_to_month:
        params["hasta (mes)"] = settings.dataestur_to_month
    return f"{url}?{urlencode(params)}" if params else url


def ingest_open_meteo(settings: Settings, dry_run: bool) -> list[str]:
    actions = []
    output_dir = RAW_DIR / "open_meteo" / "original"
    manifest_dir = RAW_DIR / "open_meteo" / "landing_manifest"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for index, location in enumerate(select_locations(settings.open_meteo_locations)):
        url = build_open_meteo_url(settings, location)
        if dry_run:
            actions.append(f"DRY-RUN ingest Open-Meteo {location.province}: GET {url} -> {output_dir}")
            continue
        existing = latest_existing_open_meteo(settings, output_dir, location)
        if existing and settings.open_meteo_skip_existing:
            actions.append(f"reused Open-Meteo {location.province} from {existing}")
            continue
        if index:
            time.sleep(settings.open_meteo_min_seconds_between_requests)
        path, manifest_path = download_file(url, output_dir, f"{location.code}_{date_range_stem(settings)}", "open_meteo")
        upload_to_s3(settings, path, f"{settings.s3_bronze_prefix}/open_meteo/original/{path.name}")
        upload_to_s3(settings, manifest_path, f"{settings.s3_bronze_prefix}/open_meteo/landing_manifest/{manifest_path.name}")
        actions.append(f"downloaded Open-Meteo {location.province} to {path}")
    return actions


def select_locations(codes: tuple[str, ...]) -> tuple[WeatherLocation, ...]:
    if not codes:
        return WEATHER_LOCATIONS
    wanted = {code.lower() for code in codes}
    selected = tuple(item for item in WEATHER_LOCATIONS if item.code in wanted)
    missing = sorted(wanted - {item.code for item in selected})
    if missing:
        raise ValueError(f"Unknown Open-Meteo locations in this script: {', '.join(missing)}")
    return selected


def build_open_meteo_url(settings: Settings, location: WeatherLocation) -> str:
    params = {
        "latitude": f"{location.latitude:.4f}",
        "longitude": f"{location.longitude:.4f}",
        "start_date": settings.open_meteo_from_date,
        "end_date": settings.open_meteo_to_date,
        "daily": ",".join(DAILY_WEATHER_VARS),
        "timezone": settings.open_meteo_timezone,
    }
    return f"{settings.open_meteo_base_url}?{urlencode(params)}"


def latest_existing_open_meteo(settings: Settings, output_dir: Path, location: WeatherLocation) -> Path | None:
    candidates = sorted(output_dir.glob(f"{location.code}_{date_range_stem(settings)}_*.json"))
    candidates = [path for path in candidates if not path.name.endswith(".metadata.json")]
    return candidates[-1] if candidates else None


def date_range_stem(settings: Settings) -> str:
    return f"{settings.open_meteo_from_date.replace('-', '')}_{settings.open_meteo_to_date.replace('-', '')}"


def download_file(url: str, output_dir: Path, stem: str, source: str) -> tuple[Path, Path]:
    validate_https_url(url)
    response = http_get(url)
    content_type = response.headers.get("content-type", "application/octet-stream")
    suffix = guess_suffix(url, content_type, response.content)
    if len(response.content) < 2:
        raise RuntimeError(f"{source} returned an empty response.")
    downloaded_at = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"{stem}_{downloaded_at}{suffix}"
    path.write_bytes(response.content)
    manifest_path = path.with_suffix(path.suffix + ".metadata.json")
    manifest_path.write_text(
        json.dumps(
            {
                "source": source,
                "url": url,
                "downloaded_at": downloaded_at,
                "content_type": content_type,
                "bytes_written": len(response.content),
                "local_path": str(path),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path, manifest_path


def http_get(url: str):
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc
    response = requests.get(url, headers={"user-agent": "tourism-weather-ml/1.0"}, timeout=300)
    if response.status_code >= 400:
        preview = response.text[:500].replace("\n", " ")
        raise RuntimeError(f"HTTP {response.status_code} for {url}. Response preview: {preview}")
    return response


def validate_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are accepted: {url}")


def guess_suffix(url: str, content_type: str, content: bytes) -> str:
    suffix = Path(urlparse(url).path).suffix
    if suffix:
        return suffix
    if "json" in content_type or content.lstrip().startswith(b"{"):
        return ".json"
    if "spreadsheet" in content_type or "excel" in content_type or content.startswith(b"PK"):
        return ".xlsx"
    if "csv" in content_type or b";" in content[:2048]:
        return ".csv"
    return ".bin"


def upload_to_s3(settings: Settings, path: Path, key: str) -> None:
    if SKIP_S3_UPLOAD or not settings.s3_bucket_name:
        return
    aws_client(settings, "s3").upload_file(str(path), settings.s3_bucket_name, key)


def upload_table_outputs_to_s3(settings: Settings, csv_path: Path, s3_prefix: str) -> None:
    upload_to_s3(settings, csv_path, f"{s3_prefix}/csv/{csv_path.name}")
    parquet_path = csv_path.with_suffix(".parquet")
    if parquet_path.exists():
        upload_to_s3(settings, parquet_path, f"{s3_prefix}/parquet/{parquet_path.name}")


def process(settings: Settings, dry_run: bool, source: str | None = None) -> list[str]:
    actions = []
    selected = (source,) if source else ("open_meteo", "dataestur", "holidays", "aena")
    if "open_meteo" in selected:
        actions.extend(process_open_meteo(settings, dry_run))
    if "dataestur" in selected:
        actions.extend(process_dataestur_inventory(settings, dry_run))
        actions.extend(process_dataestur_hotel_occupancy(settings, dry_run))
    if "holidays" in selected:
        actions.extend(process_holidays(settings, dry_run))
    if "aena" in selected:
        actions.extend(process_aena(settings, dry_run))
    unsupported = set(selected) - {"open_meteo", "dataestur", "holidays", "aena"}
    for item in sorted(unsupported):
        actions.append(f"skipped {item}: no processing step in the default Open-Meteo pipeline")
    if not dry_run:
        actions.extend(write_gold_feature_table(settings))
    return actions


def process_open_meteo(settings: Settings, dry_run: bool) -> list[str]:
    files = sorted((RAW_DIR / "open_meteo" / "original").glob("*.json"))
    files = [path for path in files if not path.name.endswith(".metadata.json")]
    output_path = PROCESSED_DIR / "silver" / "open_meteo_monthly.csv"
    if dry_run:
        return [f"DRY-RUN process {len(files)} Open-Meteo JSON files -> {output_path}"]
    rows = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        code = path.name.split("_201", 1)[0]
        province = next((item.province for item in WEATHER_LOCATIONS if item.code == code), code)
        for index, day in enumerate(dates):
            row = {"province": province, "date": day, "year_month": day[:7]}
            for variable in DAILY_WEATHER_VARS:
                values = daily.get(variable) or []
                row[variable] = values[index] if index < len(values) else None
            rows.append(row)
    monthly = aggregate_weather_monthly(rows)
    write_csv(output_path, monthly)
    maybe_write_parquet(output_path.with_suffix(".parquet"), monthly)
    upload_table_outputs_to_s3(settings, output_path, f"{settings.s3_silver_prefix}/open_meteo/open_meteo_monthly")
    return [f"processed Open-Meteo monthly table with {len(monthly)} rows -> {output_path}"]


def aggregate_weather_monthly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["province"], row["year_month"]), []).append(row)
    output = []
    for (province, year_month), group in sorted(grouped.items()):
        item: dict[str, Any] = {"province": province, "year_month": year_month, "days": len(group)}
        for variable in DAILY_WEATHER_VARS:
            values = [float(row[variable]) for row in group if row.get(variable) is not None]
            if not values:
                item[f"{variable}_avg"] = ""
                continue
            if variable.endswith("_sum") or variable == "precipitation_hours":
                item[f"{variable}_total"] = round(sum(values), 4)
            else:
                item[f"{variable}_avg"] = round(sum(values) / len(values), 4)
        output.append(item)
    return output


def process_dataestur_inventory(settings: Settings, dry_run: bool) -> list[str]:
    files = [
        path
        for path in sorted((RAW_DIR / "dataestur" / "original").glob("*"))
        if path.is_file() and not path.name.endswith(".metadata.json")
    ]
    output_path = PROCESSED_DIR / "silver" / "dataestur_inventory.csv"
    if dry_run:
        return [f"DRY-RUN process {len(files)} Dataestur raw files -> {output_path}"]
    rows = []
    for path in files:
        rows.append(
            {
                "file_name": path.name,
                "suffix": path.suffix.lower(),
                "bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
            }
        )
    write_csv(output_path, rows)
    upload_table_outputs_to_s3(settings, output_path, f"{settings.s3_silver_prefix}/dataestur/dataestur_inventory")
    return [f"processed Dataestur inventory with {len(rows)} files -> {output_path}"]


def process_dataestur_hotel_occupancy(settings: Settings, dry_run: bool) -> list[str]:
    input_path = latest_dataestur_hotel_file()
    output_path = PROCESSED_DIR / "silver" / "dataestur_hotel_occupancy_by_province.csv"
    if dry_run:
        status = f"from {input_path}" if input_path else "missing raw hotel occupancy file"
        return [f"DRY-RUN process Dataestur hotel occupancy ({status}) -> {output_path}"]
    if input_path is None:
        return ["skipped Dataestur hotel occupancy: raw hotel occupancy file is missing"]

    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install Dataestur processing dependencies with `pip install pandas openpyxl`.") from exc

    data = pd.read_excel(input_path)
    data = data[data["LUGAR_RESIDENCIA"].astype(str).str.strip().eq("Total")].copy()
    rows: list[dict[str, Any]] = []
    for _, item in data.iterrows():
        year = int(item["AÑO"])
        month = int(item["MES"])
        rows.append(
            {
                "province": normalize_dataestur_province(item["PROVINCIA"]),
                "year": year,
                "month": month,
                "year_month": f"{year:04d}-{month:02d}",
                "ccaa": item.get("CCAA", ""),
                "hotel_travelers": clean_number(item.get("VIAJEROS")),
                "hotel_overnights": clean_number(item.get("PERNOCTACIONES")),
                "hotel_avg_stay": clean_number(item.get("ESTANCIA_MEDIA")),
                "hotel_establishments_estimated": clean_number(item.get("ESTABLECIMIENTOS_ESTIMADOS")),
                "hotel_rooms_estimated": clean_number(item.get("HABITACIONES_ESTIMADAS")),
                "hotel_beds_estimated": clean_number(item.get("PLAZAS_ESTIMADAS")),
                "hotel_occupancy_rate": clean_number(item.get("GRADO_OCUPA_PLAZAS")),
                "hotel_weekend_occupancy_rate": clean_number(item.get("GRADO_OCUPA_PLAZAS_FIN_SEMANA")),
                "hotel_room_occupancy_rate": clean_number(item.get("GRADO_OCUPA_POR_HABITACIONES")),
                "hotel_staff": clean_number(item.get("PERSONAL_EMPLEADO")),
                "source_file": input_path.name,
            }
        )

    rows = sorted(rows, key=lambda row: (row["province"], row["year_month"]))
    write_csv(output_path, rows)
    maybe_write_parquet(output_path.with_suffix(".parquet"), rows)
    upload_table_outputs_to_s3(
        settings,
        output_path,
        f"{settings.s3_silver_prefix}/dataestur/dataestur_hotel_occupancy_by_province",
    )
    return [f"processed Dataestur hotel occupancy with {len(rows)} rows -> {output_path}"]


def latest_dataestur_hotel_file() -> Path | None:
    candidates = sorted((RAW_DIR / "dataestur" / "original").glob("hotel_occupancy_by_province*.xlsx"))
    return candidates[-1] if candidates else None


def process_holidays(settings: Settings, dry_run: bool) -> list[str]:
    input_path = RAW_DIR / "holidays" / "original" / (
        f"spanish_holidays_{settings.holidays_from_year}_{settings.holidays_to_year}.csv"
    )
    output_path = PROCESSED_DIR / "silver" / "holidays_calendar.csv"
    if dry_run:
        exists = "exists" if input_path.exists() else "missing"
        return [f"DRY-RUN process Spanish holidays calendar ({exists}) -> {output_path}"]
    if not input_path.exists():
        rows = build_holiday_rows(settings)
        input_path.parent.mkdir(parents=True, exist_ok=True)
        write_csv(input_path, rows)
    rows = read_csv_dicts(input_path)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        day = datetime.fromisoformat(row["date"])
        enriched.append(
            {
                **row,
                "year": day.year,
                "month": day.month,
                "year_month": row["date"][:7],
                "day_of_week": day.weekday(),
                "is_weekend": day.weekday() >= 5,
            }
        )
    write_csv(output_path, enriched)
    maybe_write_parquet(output_path.with_suffix(".parquet"), enriched)
    upload_table_outputs_to_s3(settings, output_path, f"{settings.s3_silver_prefix}/holidays/holidays_calendar")
    return [f"processed Spanish holidays calendar with {len(enriched)} rows -> {output_path}"]


def process_aena(settings: Settings, dry_run: bool) -> list[str]:
    files = sorted((RAW_DIR / "aena").glob("*.xls")) + sorted((RAW_DIR / "aena").glob("*.xlsx"))
    output_path = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic.csv"
    province_output_path = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic_by_province.csv"
    if dry_run:
        return [f"DRY-RUN process {len(files)} AENA Excel files -> {output_path}"]
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(parse_aena_file(path))
    write_csv(output_path, rows)
    maybe_write_parquet(output_path.with_suffix(".parquet"), rows)
    province_rows = aggregate_aena_by_province(rows)
    write_csv(province_output_path, province_rows)
    maybe_write_parquet(province_output_path.with_suffix(".parquet"), province_rows)
    upload_table_outputs_to_s3(settings, output_path, f"{settings.s3_silver_prefix}/aena/aena_monthly_air_traffic")
    upload_table_outputs_to_s3(
        settings,
        province_output_path,
        f"{settings.s3_silver_prefix}/aena/aena_monthly_air_traffic_by_province",
    )
    return [
        f"processed AENA airport-month table with {len(rows)} rows -> {output_path}",
        f"processed AENA province-month table with {len(province_rows)} rows -> {province_output_path}",
    ]


def parse_aena_file(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install AENA processing dependencies with `pip install pandas xlrd openpyxl`.") from exc

    year, month = parse_aena_file_date(path)
    sheet_name, data, title_row = find_aena_data_sheet(path, pd)
    pairs = aena_block_pairs(data, title_row + 1)
    metrics: dict[str, dict[str, int]] = {}
    display_names: dict[str, str] = {}
    for metric, (name_col, total_col) in zip(("passengers", "operations", "cargo_kg"), pairs):
        block = extract_aena_metric_block(data, title_row, name_col, total_col)
        metrics[metric] = block
        for normalized_name, value in block.items():
            if value is not None:
                display_names.setdefault(normalized_name, normalized_name.title())

    airports = sorted(set().union(*(set(block) for block in metrics.values())))
    missing_mapping = sorted(airport for airport in airports if airport not in AENA_AIRPORT_PROVINCES)
    if missing_mapping:
        raise ValueError(f"Missing AENA airport province mapping: {', '.join(missing_mapping)}")

    rows = []
    for airport in airports:
        rows.append(
            {
                "year": year,
                "month": month,
                "year_month": f"{year:04d}-{month:02d}",
                "airport_name": display_names.get(airport, airport.title()),
                "airport_normalized": airport,
                "province": AENA_AIRPORT_PROVINCES[airport],
                "passengers": metrics.get("passengers", {}).get(airport, 0),
                "operations": metrics.get("operations", {}).get(airport, 0),
                "cargo_kg": metrics.get("cargo_kg", {}).get(airport, 0),
                "source_file": path.name,
                "source_sheet": sheet_name,
            }
        )
    return rows


def parse_aena_file_date(path: Path) -> tuple[int, int]:
    month_match = re.match(r"(\d{2})[._]", path.name)
    year_match = re.search(r"(20\d{2})", path.name)
    if not month_match or not year_match:
        raise ValueError(f"Cannot parse AENA month/year from file name: {path.name}")
    return int(year_match.group(1)), int(month_match.group(1))


def find_aena_data_sheet(path: Path, pd):
    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        data = pd.read_excel(path, header=None, sheet_name=sheet_name)
        max_row = min(20, len(data) - 2)
        for row_index in range(max_row):
            row_text = " ".join(normalize_text(data.iat[row_index, col]) for col in range(data.shape[1]))
            next_row_text = " ".join(
                normalize_text(data.iat[row_index + 1, col]) for col in range(data.shape[1])
            )
            if (
                "PASAJEROS" in row_text
                and "OPERACIONES" in row_text
                and "MERCANCIA" in row_text
                and "AEROPUERTOS" in next_row_text
                and "TOTAL" in next_row_text
            ):
                return sheet_name, data, row_index
    raise ValueError(f"No AENA data table found in {path.name}")


def aena_block_pairs(data, header_row: int) -> list[tuple[int, int]]:
    airport_columns = [
        col for col in range(data.shape[1]) if "AEROPUERTOS" in normalize_text(data.iat[header_row, col])
    ]
    total_columns = [
        col for col in range(data.shape[1]) if normalize_text(data.iat[header_row, col]) == "TOTAL"
    ]
    if len(airport_columns) != 3 or len(total_columns) < 3:
        raise ValueError(f"Unexpected AENA header layout: airports={airport_columns}, totals={total_columns}")
    pairs = []
    for airport_col in airport_columns:
        total_col = next((col for col in total_columns if col > airport_col), None)
        if total_col is None:
            raise ValueError(f"No total column found after AENA airport column {airport_col}")
        pairs.append((airport_col, total_col))
    return pairs


def extract_aena_metric_block(data, title_row: int, name_col: int, total_col: int) -> dict[str, int]:
    total_rows = [
        row
        for row in range(title_row + 3, len(data))
        if normalize_text(data.iat[row, name_col]).startswith("TOTAL")
    ]
    if not total_rows:
        raise ValueError("No total row found in AENA metric block")
    end_row = total_rows[0]
    values: dict[str, int] = {}
    for row in range(title_row + 3, end_row):
        airport = normalize_airport_name(data.iat[row, name_col])
        if not airport:
            continue
        raw_value = data.iat[row, total_col]
        values[airport] = int(float(raw_value)) if raw_value == raw_value else 0
    return values


def aggregate_aena_by_province(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["province"], row["year_month"])
        item = grouped.setdefault(
            key,
            {
                "province": row["province"],
                "year_month": row["year_month"],
                "passengers": 0,
                "operations": 0,
                "cargo_kg": 0,
                "airport_count": 0,
            },
        )
        item["passengers"] += int(row["passengers"])
        item["operations"] += int(row["operations"])
        item["cargo_kg"] += int(row["cargo_kg"])
        item["airport_count"] += 1
    return sorted(grouped.values(), key=lambda item: (item["province"], item["year_month"]))


def write_gold_feature_table(settings: Settings) -> list[str]:
    weather_path = PROCESSED_DIR / "silver" / "open_meteo_monthly.csv"
    output_path = PROCESSED_DIR / "gold" / "tourism_weather_monthly_features.csv"
    if not weather_path.exists():
        return ["skipped gold feature table: Open-Meteo silver table is missing"]
    rows = read_csv_dicts(weather_path)
    holiday_counts = monthly_holiday_counts()
    aena_by_province = monthly_aena_by_province()
    hotel_occupancy = monthly_hotel_occupancy_by_province()
    for row in rows:
        region_code = PROVINCE_REGION_CODES.get(row["province"], "")
        national = holiday_counts.get((row["year_month"], "ES"), 0)
        regional = holiday_counts.get((row["year_month"], region_code), 0)
        aena = aena_by_province.get((row["province"], row["year_month"]), {})
        hotel = hotel_occupancy.get((row["province"], row["year_month"]), {})
        row["region_code"] = region_code
        row["national_holiday_count"] = national
        row["regional_holiday_count"] = regional
        row["total_holiday_count"] = national + regional
        row["aena_passengers"] = aena.get("passengers", 0)
        row["aena_operations"] = aena.get("operations", 0)
        row["aena_cargo_kg"] = aena.get("cargo_kg", 0)
        row["aena_airport_count"] = aena.get("airport_count", 0)
        row["hotel_travelers"] = hotel.get("hotel_travelers", "")
        row["hotel_overnights"] = hotel.get("hotel_overnights", "")
        row["hotel_avg_stay"] = hotel.get("hotel_avg_stay", "")
        row["hotel_establishments_estimated"] = hotel.get("hotel_establishments_estimated", "")
        row["hotel_rooms_estimated"] = hotel.get("hotel_rooms_estimated", "")
        row["hotel_beds_estimated"] = hotel.get("hotel_beds_estimated", "")
        row["hotel_occupancy_rate"] = hotel.get("hotel_occupancy_rate", "")
        row["hotel_weekend_occupancy_rate"] = hotel.get("hotel_weekend_occupancy_rate", "")
        row["hotel_room_occupancy_rate"] = hotel.get("hotel_room_occupancy_rate", "")
        row["hotel_staff"] = hotel.get("hotel_staff", "")
        row["target_available"] = bool(hotel.get("hotel_overnights"))
        row["feature_source"] = "open_meteo_monthly+holidays+aena+dataestur_hotel"
    write_csv(output_path, rows)
    maybe_write_parquet(output_path.with_suffix(".parquet"), rows)
    upload_table_outputs_to_s3(settings, output_path, f"{settings.s3_gold_prefix}/tourism_weather_monthly_features")
    return [f"wrote gold feature table with {len(rows)} rows -> {output_path}"]


def monthly_holiday_counts() -> dict[tuple[str, str], int]:
    holidays_path = PROCESSED_DIR / "silver" / "holidays_calendar.csv"
    if not holidays_path.exists():
        return {}
    counts: dict[tuple[str, str], int] = {}
    for row in read_csv_dicts(holidays_path):
        if row.get("scope") not in {"national", "regional"}:
            continue
        key = (row["year_month"], row["region_code"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def monthly_aena_by_province() -> dict[tuple[str, str], dict[str, int]]:
    path = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic_by_province.csv"
    if not path.exists():
        return {}
    values: dict[tuple[str, str], dict[str, int]] = {}
    for row in read_csv_dicts(path):
        values[(row["province"], row["year_month"])] = {
            "passengers": int(float(row["passengers"] or 0)),
            "operations": int(float(row["operations"] or 0)),
            "cargo_kg": int(float(row["cargo_kg"] or 0)),
            "airport_count": int(float(row["airport_count"] or 0)),
        }
    return values


def monthly_hotel_occupancy_by_province() -> dict[tuple[str, str], dict[str, str]]:
    path = PROCESSED_DIR / "silver" / "dataestur_hotel_occupancy_by_province.csv"
    if not path.exists():
        return {}
    values: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv_dicts(path):
        values[(row["province"], row["year_month"])] = row
    return values


ATHENA_PARQUET_TABLES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "silver_open_meteo_monthly": (
        "silver/open_meteo/open_meteo_monthly/parquet/",
        [
            ("province", "string"),
            ("year_month", "string"),
            ("days", "int"),
            ("temperature_2m_mean_avg", "double"),
            ("temperature_2m_max_avg", "double"),
            ("temperature_2m_min_avg", "double"),
            ("precipitation_sum_total", "double"),
            ("rain_sum_total", "double"),
            ("precipitation_hours_total", "double"),
            ("wind_speed_10m_mean_avg", "double"),
            ("wind_speed_10m_max_avg", "double"),
        ],
    ),
    "silver_dataestur_hotel_occupancy_by_province": (
        "silver/dataestur/dataestur_hotel_occupancy_by_province/parquet/",
        [
            ("province", "string"),
            ("year", "int"),
            ("month", "int"),
            ("year_month", "string"),
            ("ccaa", "string"),
            ("hotel_travelers", "double"),
            ("hotel_overnights", "double"),
            ("hotel_avg_stay", "double"),
            ("hotel_establishments_estimated", "double"),
            ("hotel_rooms_estimated", "double"),
            ("hotel_beds_estimated", "double"),
            ("hotel_occupancy_rate", "double"),
            ("hotel_weekend_occupancy_rate", "double"),
            ("hotel_room_occupancy_rate", "double"),
            ("hotel_staff", "double"),
            ("source_file", "string"),
        ],
    ),
    "silver_holidays_calendar": (
        "silver/holidays/holidays_calendar/parquet/",
        [
            ("date", "string"),
            ("country", "string"),
            ("region_code", "string"),
            ("region_name", "string"),
            ("holiday_name", "string"),
            ("scope", "string"),
            ("year", "int"),
            ("month", "int"),
            ("year_month", "string"),
            ("day_of_week", "int"),
            ("is_weekend", "boolean"),
        ],
    ),
    "silver_aena_monthly_air_traffic": (
        "silver/aena/aena_monthly_air_traffic/parquet/",
        [
            ("year", "int"),
            ("month", "int"),
            ("year_month", "string"),
            ("airport_name", "string"),
            ("airport_normalized", "string"),
            ("province", "string"),
            ("passengers", "bigint"),
            ("operations", "bigint"),
            ("cargo_kg", "bigint"),
            ("source_file", "string"),
            ("source_sheet", "string"),
        ],
    ),
    "silver_aena_monthly_air_traffic_by_province": (
        "silver/aena/aena_monthly_air_traffic_by_province/parquet/",
        [
            ("province", "string"),
            ("year_month", "string"),
            ("passengers", "bigint"),
            ("operations", "bigint"),
            ("cargo_kg", "bigint"),
            ("airport_count", "int"),
        ],
    ),
    "gold_tourism_weather_monthly_features": (
        "gold/tourism_weather_monthly_features/parquet/",
        [
            ("province", "string"),
            ("year_month", "string"),
            ("days", "int"),
            ("temperature_2m_mean_avg", "double"),
            ("temperature_2m_max_avg", "double"),
            ("temperature_2m_min_avg", "double"),
            ("precipitation_sum_total", "double"),
            ("rain_sum_total", "double"),
            ("precipitation_hours_total", "double"),
            ("wind_speed_10m_mean_avg", "double"),
            ("wind_speed_10m_max_avg", "double"),
            ("region_code", "string"),
            ("national_holiday_count", "int"),
            ("regional_holiday_count", "int"),
            ("total_holiday_count", "int"),
            ("aena_passengers", "bigint"),
            ("aena_operations", "bigint"),
            ("aena_cargo_kg", "bigint"),
            ("aena_airport_count", "int"),
            ("hotel_travelers", "double"),
            ("hotel_overnights", "double"),
            ("hotel_avg_stay", "double"),
            ("hotel_establishments_estimated", "double"),
            ("hotel_rooms_estimated", "double"),
            ("hotel_beds_estimated", "double"),
            ("hotel_occupancy_rate", "double"),
            ("hotel_weekend_occupancy_rate", "double"),
            ("hotel_room_occupancy_rate", "double"),
            ("hotel_staff", "double"),
            ("target_available", "boolean"),
            ("feature_source", "string"),
        ],
    ),
}


def catalog_athena_tables(settings: Settings, dry_run: bool) -> list[str]:
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is required to catalog Athena tables.")
    if not settings.athena_results_s3_uri:
        raise ValueError("ATHENA_RESULTS_S3_URI is required to run Athena DDL.")
    actions = [
        f"ensure Glue database exists: {settings.glue_database}",
        f"create/update {len(ATHENA_PARQUET_TABLES)} Athena external Parquet tables",
    ]
    if dry_run:
        return [f"DRY-RUN {action}" for action in actions] + [
            f"DRY-RUN table {name} -> s3://{settings.s3_bucket_name}/{location}"
            for name, (location, _columns) in ATHENA_PARQUET_TABLES.items()
        ]

    ensure_glue_database(settings)
    ensure_athena_workgroup(settings)
    for table_name, (location, columns) in ATHENA_PARQUET_TABLES.items():
        query = athena_create_parquet_table_sql(settings, table_name, location, columns)
        run_athena_query(settings, query)
        actions.append(f"cataloged Athena table {settings.glue_database}.{table_name}")
    validation_query = (
        "SELECT COUNT(*) AS rows, COUNT(hotel_overnights) AS target_rows "
        "FROM gold_tourism_weather_monthly_features"
    )
    query_id = run_athena_query(settings, validation_query)
    actions.append(f"validated gold table with Athena query {query_id}")
    return actions


def athena_create_parquet_table_sql(
    settings: Settings,
    table_name: str,
    location: str,
    columns: list[tuple[str, str]],
) -> str:
    column_sql = ",\n  ".join(f"`{name}` {athena_type}" for name, athena_type in columns)
    s3_location = f"s3://{settings.s3_bucket_name}/{location}"
    return f"""
CREATE EXTERNAL TABLE IF NOT EXISTS `{settings.glue_database}`.`{table_name}` (
  {column_sql}
)
STORED AS PARQUET
LOCATION '{s3_location}'
TBLPROPERTIES ('parquet.compression'='SNAPPY')
"""


def run_athena_query(settings: Settings, query: str) -> str:
    athena = aws_client(settings, "athena")
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": settings.glue_database},
        WorkGroup=settings.athena_workgroup,
        ResultConfiguration={"OutputLocation": settings.athena_results_s3_uri},
    )
    query_id = response["QueryExecutionId"]
    deadline = time.monotonic() + ATHENA_QUERY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            return query_id
        if state in {"FAILED", "CANCELLED"}:
            reason = execution["Status"].get("StateChangeReason", "unknown")
            raise RuntimeError(f"Athena query {query_id} {state}: {reason}")
        time.sleep(ATHENA_QUERY_POLL_SECONDS)
    raise TimeoutError(f"Athena query {query_id} did not finish in time.")


def normalize_text(value: Any) -> str:
    if value is None or value != value:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().upper())
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip()


def normalize_airport_name(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = re.sub(r"\s*\(\*+\)\s*$", "", text)
    text = re.sub(r"\s*/\s*", "-", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_dataestur_province(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    if text in DATAESTUR_PROVINCE_ALIASES:
        return DATAESTUR_PROVINCE_ALIASES[text]
    for province in PROVINCE_REGION_CODES:
        if normalize_text(province) == text:
            return province
    return str(value).strip()


def clean_number(value: Any) -> int | float | None:
    if value is None or value != value:
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return round(number, 4)


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def maybe_write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    try:
        import pandas as pd
    except ImportError:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if column in PARQUET_STRING_COLUMNS:
            continue
        if column == "target_available":
            frame[column] = frame[column].map(
                lambda value: value
                if isinstance(value, bool)
                else str(value).strip().lower() in {"true", "1", "yes"}
            )
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().sum() or frame[column].isna().all():
            frame[column] = converted
    frame.to_parquet(path, index=False)


def safe_stem(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def main() -> int:
    global SKIP_S3_UPLOAD
    args = parse_args()
    SKIP_S3_UPLOAD = args.skip_s3_upload
    configure_logging(args.log_level)
    settings = get_settings()

    if args.list_dataestur:
        for endpoint, name in DATAESTUR_ENDPOINTS.items():
            print(f"- {endpoint}: {name}")
        return 0
    if args.check_config:
        print_config_check(settings)
        return 0
    if args.ingest and args.skip_ingest:
        raise SystemExit("Use either --ingest or --skip-ingest, not both.")

    run_all = not any((args.deploy, args.ingest, args.process, args.catalog))
    missing = []
    if not args.dry_run and (args.deploy or run_all):
        missing.extend(settings.required_aws_values)
    if missing:
        raise SystemExit(f"Missing required configuration: {', '.join(dict.fromkeys(missing))}")

    started_at = time.perf_counter()
    actions: list[str] = []
    if args.deploy or run_all:
        LOGGER.info("Deploy phase started")
        actions.extend(provision(settings, args.dry_run))
    if args.ingest or (run_all and not args.skip_ingest):
        LOGGER.info("Ingestion phase started")
        actions.extend(ingest(settings, args))
    if args.process or run_all:
        LOGGER.info("Processing phase started")
        actions.extend(process(settings, args.dry_run, args.source))
    if args.catalog:
        LOGGER.info("Catalog phase started")
        actions.extend(catalog_athena_tables(settings, args.dry_run))

    for action in actions:
        print(f"- {action}")
    LOGGER.info("Pipeline finished in %.1fs", time.perf_counter() - started_at)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        LOGGER.exception("Pipeline failed")
        raise
