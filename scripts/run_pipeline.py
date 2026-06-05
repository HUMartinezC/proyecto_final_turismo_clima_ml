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
    for linea in path.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        clave, valor = limpia.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str | None:
    valor = os.getenv(name, default)
    return valor if valor not in {"", None} else None


def parse_csv(valor: str | None) -> tuple[str, ...]:
    if not valor:
        return ()
    return tuple(elemento.strip().strip("/") for elemento in valor.split(",") if elemento.strip())


def parse_named_urls(valor: str | None) -> dict[str, str]:
    urls: dict[str, str] = {}
    if not valor:
        return urls
    for elemento in valor.split(";"):
        if "=" not in elemento:
            continue
        name, url = elemento.split("=", 1)
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
        faltantes = []
        if not self.s3_bucket_name:
            faltantes.append("S3_BUCKET_NAME")
        if not self.athena_results_s3_uri:
            faltantes.append("ATHENA_RESULTS_S3_URI")
        return faltantes

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


def boto3_session(configuracion: Settings):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc

    argumentos: dict[str, str] = {"region_name": configuracion.aws_region}
    tiene_credenciales_entorno = bool(env("AWS_ACCESS_KEY_ID") and env("AWS_SECRET_ACCESS_KEY"))
    if configuracion.aws_profile and not tiene_credenciales_entorno:
        argumentos["profile_name"] = configuracion.aws_profile
    return boto3.Session(**argumentos)


def aws_client(configuracion: Settings, service: str):
    return boto3_session(configuracion).client(service)


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


def print_config_check(configuracion: Settings) -> None:
    checks = {
        "AWS_REGION": configuracion.aws_region,
        "AWS_PROFILE": configuracion.aws_profile or "<env/default credential chain>",
        "S3_BUCKET_NAME": "configured" if configuracion.s3_bucket_name else "missing",
        "ATHENA_RESULTS_S3_URI": "configured" if configuracion.athena_results_s3_uri else "missing",
        "GLUE_DATABASE": configuracion.glue_database,
        "RDS_INSTANCE_IDENTIFIER": configuracion.rds_instance_identifier,
        "RDS_USER": "configured" if configuracion.rds_user else "missing",
        "RDS_PASSWORD": "configured" if configuracion.rds_password else "missing",
        "DOCDB_URI": "configured" if configuracion.docdb_uri else "missing",
        "KAFKA_BOOTSTRAP_SERVERS": "configured" if configuracion.kafka_bootstrap_servers else "missing",
        "LAMBDA_ROLE_ARN": "configured" if configuracion.lambda_role_arn else "missing",
        "OPEN_METEO_RANGE": f"{configuracion.open_meteo_from_date} to {configuracion.open_meteo_to_date}",
        "OPEN_METEO_LOCATIONS": ", ".join(configuracion.open_meteo_locations) or "all province capitals",
        "HOLIDAYS_RANGE": f"{configuracion.holidays_from_year} to {configuracion.holidays_to_year}",
        "DATAESTUR_ENDPOINTS": ", ".join(configuracion.dataestur_endpoints),
    }
    for clave, valor in checks.items():
        print(f"- {clave}: {valor}")


def provision(configuracion: Settings, dry_run: bool) -> list[str]:
    acciones = [
        "validate AWS identity with STS",
        f"ensure S3 bucket and lake prefixes: {configuracion.s3_bucket_name}",
        f"ensure Glue database: {configuracion.glue_database}",
        f"ensure Athena workgroup: {configuracion.athena_workgroup}",
        f"ensure RDS MariaDB instance: {configuracion.rds_instance_identifier}",
        f"prepare Lambda function when LAMBDA_ROLE_ARN is configured: {configuracion.lambda_function_name}",
        "validate DocumentDB and Kafka configuration when provided",
    ]
    if dry_run:
        return [f"DRY-RUN {action}" for action in acciones]

    aws_client(configuracion, "sts").get_caller_identity()
    ensure_bucket(configuracion)
    ensure_glue_database(configuracion)
    ensure_athena_workgroup(configuracion)
    ensure_rds_instance(configuracion)
    ensure_lambda_function(configuracion)
    return acciones


def ensure_bucket(configuracion: Settings) -> None:
    if not configuracion.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is required.")
    s3 = aws_client(configuracion, "s3")
    try:
        s3.head_bucket(Bucket=configuracion.s3_bucket_name)
    except Exception:
        argumentos_creacion: dict[str, Any] = {"Bucket": configuracion.s3_bucket_name}
        if configuracion.aws_region != "us-east-1":
            argumentos_creacion["CreateBucketConfiguration"] = {"LocationConstraint": configuracion.aws_region}
        s3.create_bucket(**argumentos_creacion)
        s3.get_waiter("bucket_exists").wait(Bucket=configuracion.s3_bucket_name)
    for prefijo in (configuracion.s3_bronze_prefix, configuracion.s3_silver_prefix, configuracion.s3_gold_prefix):
        s3.put_object(Bucket=configuracion.s3_bucket_name, Key=f"{prefijo}/")


def ensure_glue_database(configuracion: Settings) -> None:
    glue = aws_client(configuracion, "glue")
    try:
        glue.get_database(Name=configuracion.glue_database)
    except Exception:
        glue.create_database(DatabaseInput={"Name": configuracion.glue_database})


def ensure_athena_workgroup(configuracion: Settings) -> None:
    if not configuracion.athena_results_s3_uri:
        raise ValueError("ATHENA_RESULTS_S3_URI is required.")
    cliente_athena = aws_client(configuracion, "athena")
    try:
        cliente_athena.get_work_group(WorkGroup=configuracion.athena_workgroup)
    except Exception:
        cliente_athena.create_work_group(
            Name=configuracion.athena_workgroup,
            Configuration={"ResultConfiguration": {"OutputLocation": configuracion.athena_results_s3_uri}},
            Description="Tourism-weather ML workgroup",
        )


def ensure_rds_instance(configuracion: Settings) -> None:
    if not configuracion.rds_user or not configuracion.rds_password:
        LOGGER.warning("Skipping RDS creation because RDS_USER/RDS_PASSWORD are missing.")
        return
    rds = aws_client(configuracion, "rds")
    try:
        rds.describe_db_instances(DBInstanceIdentifier=configuracion.rds_instance_identifier)
        return
    except Exception:
        pass
    rds.create_db_instance(
        DBInstanceIdentifier=configuracion.rds_instance_identifier,
        DBInstanceClass=configuracion.rds_instance_class,
        Engine="mariadb",
        AllocatedStorage=configuracion.rds_allocated_storage,
        DBName=configuracion.rds_database,
        MasterUsername=configuracion.rds_user,
        MasterUserPassword=configuracion.rds_password,
        Port=configuracion.rds_port,
        PubliclyAccessible=configuracion.rds_publicly_accessible,
        BackupRetentionPeriod=0,
        DeletionProtection=False,
    )


def ensure_lambda_function(configuracion: Settings) -> None:
    if not configuracion.lambda_role_arn:
        LOGGER.warning("Skipping Lambda creation because LAMBDA_ROLE_ARN is missing.")
        return
    lambda_client = aws_client(configuracion, "lambda")
    code = (
        "def handler(event, context):\n"
        "    return {'statusCode': 200, 'body': 'tourism-weather ingestion placeholder'}\n"
    )
    buffer_zip = BytesIO()
    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
        archivo_zip.writestr("lambda_function.py", code)
    try:
        lambda_client.get_function(FunctionName=configuracion.lambda_function_name)
        lambda_client.update_function_code(
            FunctionName=configuracion.lambda_function_name,
            ZipFile=buffer_zip.getvalue(),
        )
    except Exception:
        lambda_client.create_function(
            FunctionName=configuracion.lambda_function_name,
            Runtime="python3.11",
            Role=configuracion.lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": buffer_zip.getvalue()},
            Description="Course project ingestion automation placeholder",
        )


def ingest(configuracion: Settings, argumentos_cli: argparse.Namespace) -> list[str]:
    acciones: list[str] = []
    seleccionados = (argumentos_cli.source,) if argumentos_cli.source else ("dataestur", "open_meteo", "holidays", "aena")
    for fuente in seleccionados:
        try:
            if fuente == "dataestur":
                acciones.extend(ingest_dataestur(configuracion, argumentos_cli))
            elif fuente == "open_meteo":
                acciones.extend(ingest_open_meteo(configuracion, argumentos_cli.dry_run))
            elif fuente == "holidays":
                acciones.extend(ingest_holidays(configuracion, argumentos_cli.dry_run))
            elif fuente == "aena":
                acciones.extend(ingest_aena(configuracion, argumentos_cli.dry_run))
            elif fuente == "aemet":
                acciones.append(
                    "skipped aemet: optional contrast source, not part of the default "
                    "single-file pipeline"
                )
            else:
                acciones.append(f"skipped {fuente}: connector not implemented in this single-file MVP")
        except Exception as exc:
            LOGGER.error("%s ingestion failed: %s", fuente, exc)
            if not argumentos_cli.continue_on_error:
                raise
            acciones.append(f"skipped {fuente} after error: {exc}")
    return acciones


def ingest_aena(configuracion: Settings, dry_run: bool) -> list[str]:
    archivos = sorted((RAW_DIR / "aena").glob("*.xls")) + sorted((RAW_DIR / "aena").glob("*.xlsx"))
    if dry_run:
        return [f"DRY-RUN register {len(archivos)} local AENA Excel files from {RAW_DIR / 'aena'}"]
    for path in archivos:
        upload_to_s3(configuracion, path, f"{configuracion.s3_bronze_prefix}/aena/original/{path.name}")
    return [f"registered {len(archivos)} local AENA Excel files from {RAW_DIR / 'aena'}"]


def ingest_holidays(configuracion: Settings, dry_run: bool) -> list[str]:
    directorio_salida = RAW_DIR / "holidays" / "original"
    directorio_salida.mkdir(parents=True, exist_ok=True)
    ruta_csv = directorio_salida / f"spanish_holidays_{configuracion.holidays_from_year}_{configuracion.holidays_to_year}.csv"
    ruta_metadatos = ruta_csv.with_suffix(ruta_csv.suffix + ".metadata.json")
    if dry_run:
        return [f"DRY-RUN generate Spanish holidays calendar -> {ruta_csv}"]

    filas = build_holiday_rows(configuracion)
    write_csv(ruta_csv, filas)
    ruta_metadatos.write_text(
        json.dumps(
            {
                "source": "python-holidays",
                "country": "ES",
                "from_year": configuracion.holidays_from_year,
                "to_year": configuracion.holidays_to_year,
                "regions": SPANISH_REGION_SUBDIVISIONS,
                "rows": len(filas),
                "generated_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                "local_path": str(ruta_csv),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    upload_to_s3(configuracion, ruta_csv, f"{configuracion.s3_bronze_prefix}/holidays/original/{ruta_csv.name}")
    upload_to_s3(
        configuracion,
        ruta_metadatos,
        f"{configuracion.s3_bronze_prefix}/holidays/landing_manifest/{ruta_metadatos.name}",
    )
    return [f"generated Spanish holidays calendar with {len(filas)} rows -> {ruta_csv}"]


def build_holiday_rows(configuracion: Settings) -> list[dict[str, Any]]:
    try:
        import holidays
    except ImportError as exc:
        raise RuntimeError("Install the holidays source with `pip install holidays pandas`.") from exc

    anios = range(configuracion.holidays_from_year, configuracion.holidays_to_year + 1)
    festivos_nacionales = holidays.country_holidays("ES", years=anios, language="es")
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, str, str, str]] = set()

    for dia, name in sorted(festivos_nacionales.items()):
        clave = (dia.isoformat(), "ES", str(name), "national")
        vistos.add(clave)
        filas.append(
            {
                "date": dia.isoformat(),
                "country": "ES",
                "region_code": "ES",
                "region_name": "España",
                "holiday_name": str(name),
                "scope": "national",
            }
        )

    for codigo_region, nombre_region in SPANISH_REGION_SUBDIVISIONS.items():
        festivos_regionales = holidays.country_holidays("ES", subdiv=codigo_region, years=anios, language="es")
        for dia, name in sorted(festivos_regionales.items()):
            if dia in festivos_nacionales and str(festivos_nacionales[dia]) == str(name):
                continue
            clave = (dia.isoformat(), codigo_region, str(name), "regional")
            if clave in vistos:
                continue
            vistos.add(clave)
            filas.append(
                {
                    "date": dia.isoformat(),
                    "country": "ES",
                    "region_code": codigo_region,
                    "region_name": nombre_region,
                    "holiday_name": str(name),
                    "scope": "regional",
                }
            )

    return sorted(filas, key=lambda fila: (fila["date"], fila["region_code"], fila["holiday_name"]))


def ingest_dataestur(configuracion: Settings, argumentos_cli: argparse.Namespace) -> list[str]:
    fuentes = configured_dataestur_sources(configuracion, tuple(argumentos_cli.dataestur_endpoint or ()))
    if argumentos_cli.dataestur_limit is not None:
        fuentes = fuentes[: argumentos_cli.dataestur_limit]
    acciones = []
    directorio_salida = RAW_DIR / "dataestur" / "original"
    directorio_manifiestos = RAW_DIR / "dataestur" / "landing_manifest"
    directorio_salida.mkdir(parents=True, exist_ok=True)
    directorio_manifiestos.mkdir(parents=True, exist_ok=True)
    for indice, (name, url) in enumerate(fuentes):
        if argumentos_cli.dry_run:
            acciones.append(f"DRY-RUN ingest Dataestur {name}: GET {url} -> {directorio_salida}")
            continue
        if indice:
            time.sleep(6.5)
        path, ruta_manifiesto = download_file(url, directorio_salida, safe_stem(name), "dataestur")
        upload_to_s3(configuracion, path, f"{configuracion.s3_bronze_prefix}/dataestur/original/{path.name}")
        upload_to_s3(configuracion, ruta_manifiesto, f"{configuracion.s3_bronze_prefix}/dataestur/landing_manifest/{ruta_manifiesto.name}")
        acciones.append(f"downloaded Dataestur {name} to {path}")
    return acciones


def configured_dataestur_sources(configuracion: Settings, endpoints: tuple[str, ...]) -> list[tuple[str, str]]:
    seleccionados = endpoints or configuracion.dataestur_endpoints or tuple(DATAESTUR_ENDPOINTS.keys())
    fuentes = [
        (DATAESTUR_ENDPOINTS.get(endpoint, endpoint.lower().removesuffix("_dl")), build_dataestur_url(configuracion, endpoint))
        for endpoint in seleccionados
    ]
    fuentes.extend(configuracion.dataestur_request_urls.items())
    return fuentes


def build_dataestur_url(configuracion: Settings, endpoint: str) -> str:
    base = configuracion.dataestur_base_url.rstrip("/") + "/"
    url = urljoin(base, endpoint.strip().strip("/"))
    parametros: dict[str, int] = {}
    if configuracion.dataestur_from_year:
        parametros["desde (año)"] = configuracion.dataestur_from_year
    if configuracion.dataestur_from_month:
        parametros["desde (mes)"] = configuracion.dataestur_from_month
    if configuracion.dataestur_to_year:
        parametros["hasta (año)"] = configuracion.dataestur_to_year
    if configuracion.dataestur_to_month:
        parametros["hasta (mes)"] = configuracion.dataestur_to_month
    return f"{url}?{urlencode(parametros)}" if parametros else url


def ingest_open_meteo(configuracion: Settings, dry_run: bool) -> list[str]:
    acciones = []
    directorio_salida = RAW_DIR / "open_meteo" / "original"
    directorio_manifiestos = RAW_DIR / "open_meteo" / "landing_manifest"
    directorio_salida.mkdir(parents=True, exist_ok=True)
    directorio_manifiestos.mkdir(parents=True, exist_ok=True)
    for indice, ubicacion in enumerate(select_locations(configuracion.open_meteo_locations)):
        url = build_open_meteo_url(configuracion, ubicacion)
        if dry_run:
            acciones.append(f"DRY-RUN ingest Open-Meteo {ubicacion.province}: GET {url} -> {directorio_salida}")
            continue
        existing = latest_existing_open_meteo(configuracion, directorio_salida, ubicacion)
        if existing and configuracion.open_meteo_skip_existing:
            acciones.append(f"reused Open-Meteo {ubicacion.province} from {existing}")
            continue
        if indice:
            time.sleep(configuracion.open_meteo_min_seconds_between_requests)
        path, ruta_manifiesto = download_file(url, directorio_salida, f"{ubicacion.code}_{date_range_stem(configuracion)}", "open_meteo")
        upload_to_s3(configuracion, path, f"{configuracion.s3_bronze_prefix}/open_meteo/original/{path.name}")
        upload_to_s3(configuracion, ruta_manifiesto, f"{configuracion.s3_bronze_prefix}/open_meteo/landing_manifest/{ruta_manifiesto.name}")
        acciones.append(f"downloaded Open-Meteo {ubicacion.province} to {path}")
    return acciones


def select_locations(codes: tuple[str, ...]) -> tuple[WeatherLocation, ...]:
    if not codes:
        return WEATHER_LOCATIONS
    wanted = {code.lower() for code in codes}
    seleccionados = tuple(elemento for elemento in WEATHER_LOCATIONS if elemento.code in wanted)
    faltantes = sorted(wanted - {elemento.code for elemento in seleccionados})
    if faltantes:
        raise ValueError(f"Unknown Open-Meteo locations in this script: {', '.join(faltantes)}")
    return seleccionados


def build_open_meteo_url(configuracion: Settings, ubicacion: WeatherLocation) -> str:
    parametros = {
        "latitude": f"{ubicacion.latitude:.4f}",
        "longitude": f"{ubicacion.longitude:.4f}",
        "start_date": configuracion.open_meteo_from_date,
        "end_date": configuracion.open_meteo_to_date,
        "daily": ",".join(DAILY_WEATHER_VARS),
        "timezone": configuracion.open_meteo_timezone,
    }
    return f"{configuracion.open_meteo_base_url}?{urlencode(parametros)}"


def latest_existing_open_meteo(configuracion: Settings, directorio_salida: Path, ubicacion: WeatherLocation) -> Path | None:
    candidates = sorted(directorio_salida.glob(f"{ubicacion.code}_{date_range_stem(configuracion)}_*.json"))
    candidates = [path for path in candidates if not path.name.endswith(".metadata.json")]
    return candidates[-1] if candidates else None


def date_range_stem(configuracion: Settings) -> str:
    return f"{configuracion.open_meteo_from_date.replace('-', '')}_{configuracion.open_meteo_to_date.replace('-', '')}"


def download_file(url: str, directorio_salida: Path, raiz_nombre: str, fuente: str) -> tuple[Path, Path]:
    validate_https_url(url)
    respuesta = http_get(url)
    tipo_contenido = respuesta.headers.get("content-type", "application/octet-stream")
    sufijo = guess_suffix(url, tipo_contenido, respuesta.content)
    if len(respuesta.content) < 2:
        raise RuntimeError(f"{fuente} returned an empty response.")
    descargado_en = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directorio_salida / f"{raiz_nombre}_{descargado_en}{sufijo}"
    path.write_bytes(respuesta.content)
    ruta_manifiesto = path.with_suffix(path.suffix + ".metadata.json")
    ruta_manifiesto.write_text(
        json.dumps(
            {
                "source": fuente,
                "url": url,
                "downloaded_at": descargado_en,
                "content_type": tipo_contenido,
                "bytes_written": len(respuesta.content),
                "local_path": str(path),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path, ruta_manifiesto


def http_get(url: str):
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt`.") from exc
    respuesta = requests.get(url, headers={"user-agent": "tourism-weather-ml/1.0"}, timeout=300)
    if respuesta.status_code >= 400:
        preview = respuesta.text[:500].replace("\n", " ")
        raise RuntimeError(f"HTTP {respuesta.status_code} for {url}. Response preview: {preview}")
    return respuesta


def validate_https_url(url: str) -> None:
    url_parseada = urlparse(url)
    if url_parseada.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are accepted: {url}")


def guess_suffix(url: str, tipo_contenido: str, contenido: bytes) -> str:
    sufijo = Path(urlparse(url).path).suffix
    if sufijo:
        return sufijo
    if "json" in tipo_contenido or contenido.lstrip().startswith(b"{"):
        return ".json"
    if "spreadsheet" in tipo_contenido or "excel" in tipo_contenido or contenido.startswith(b"PK"):
        return ".xlsx"
    if "csv" in tipo_contenido or b";" in contenido[:2048]:
        return ".csv"
    return ".bin"


def upload_to_s3(configuracion: Settings, path: Path, clave: str) -> None:
    if SKIP_S3_UPLOAD or not configuracion.s3_bucket_name:
        return
    aws_client(configuracion, "s3").upload_file(str(path), configuracion.s3_bucket_name, clave)


def upload_table_outputs_to_s3(configuracion: Settings, ruta_csv: Path, s3_prefix: str) -> None:
    upload_to_s3(configuracion, ruta_csv, f"{s3_prefix}/csv/{ruta_csv.name}")
    ruta_parquet = ruta_csv.with_suffix(".parquet")
    if ruta_parquet.exists():
        upload_to_s3(configuracion, ruta_parquet, f"{s3_prefix}/parquet/{ruta_parquet.name}")


def process(configuracion: Settings, dry_run: bool, fuente: str | None = None) -> list[str]:
    acciones = []
    seleccionados = (fuente,) if fuente else ("open_meteo", "dataestur", "holidays", "aena")
    if "open_meteo" in seleccionados:
        acciones.extend(process_open_meteo(configuracion, dry_run))
    if "dataestur" in seleccionados:
        acciones.extend(process_dataestur_inventory(configuracion, dry_run))
        acciones.extend(process_dataestur_hotel_occupancy(configuracion, dry_run))
    if "holidays" in seleccionados:
        acciones.extend(process_holidays(configuracion, dry_run))
    if "aena" in seleccionados:
        acciones.extend(process_aena(configuracion, dry_run))
    unsupported = set(seleccionados) - {"open_meteo", "dataestur", "holidays", "aena"}
    for elemento in sorted(unsupported):
        acciones.append(f"skipped {elemento}: no processing step in the default Open-Meteo pipeline")
    if not dry_run:
        acciones.extend(write_gold_feature_table(configuracion))
    return acciones


def process_open_meteo(configuracion: Settings, dry_run: bool) -> list[str]:
    archivos = sorted((RAW_DIR / "open_meteo" / "original").glob("*.json"))
    archivos = [path for path in archivos if not path.name.endswith(".metadata.json")]
    ruta_salida = PROCESSED_DIR / "silver" / "open_meteo_monthly.csv"
    if dry_run:
        return [f"DRY-RUN process {len(archivos)} Open-Meteo JSON files -> {ruta_salida}"]
    filas = []
    for path in archivos:
        carga = json.loads(path.read_text(encoding="utf-8"))
        diario = carga.get("daily", {})
        fechas = diario.get("time", [])
        code = path.name.split("_201", 1)[0]
        province = next((elemento.province for elemento in WEATHER_LOCATIONS if elemento.code == code), code)
        for indice, dia in enumerate(fechas):
            fila = {"province": province, "date": dia, "year_month": dia[:7]}
            for variable in DAILY_WEATHER_VARS:
                valores = diario.get(variable) or []
                fila[variable] = valores[indice] if indice < len(valores) else None
            filas.append(fila)
    mensual = aggregate_weather_monthly(filas)
    write_csv(ruta_salida, mensual)
    maybe_write_parquet(ruta_salida.with_suffix(".parquet"), mensual)
    upload_table_outputs_to_s3(configuracion, ruta_salida, f"{configuracion.s3_silver_prefix}/open_meteo/open_meteo_monthly")
    return [f"processed Open-Meteo monthly table with {len(mensual)} rows -> {ruta_salida}"]


def aggregate_weather_monthly(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agrupados: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fila in filas:
        agrupados.setdefault((fila["province"], fila["year_month"]), []).append(fila)
    output = []
    for (province, year_month), grupo in sorted(agrupados.items()):
        elemento: dict[str, Any] = {"province": province, "year_month": year_month, "days": len(grupo)}
        for variable in DAILY_WEATHER_VARS:
            valores = [float(fila[variable]) for fila in grupo if fila.get(variable) is not None]
            if not valores:
                elemento[f"{variable}_avg"] = ""
                continue
            if variable.endswith("_sum") or variable == "precipitation_hours":
                elemento[f"{variable}_total"] = round(sum(valores), 4)
            else:
                elemento[f"{variable}_avg"] = round(sum(valores) / len(valores), 4)
        output.append(elemento)
    return output


def process_dataestur_inventory(configuracion: Settings, dry_run: bool) -> list[str]:
    archivos = [
        path
        for path in sorted((RAW_DIR / "dataestur" / "original").glob("*"))
        if path.is_file() and not path.name.endswith(".metadata.json")
    ]
    ruta_salida = PROCESSED_DIR / "silver" / "dataestur_inventory.csv"
    if dry_run:
        return [f"DRY-RUN process {len(archivos)} Dataestur raw files -> {ruta_salida}"]
    filas = []
    for path in archivos:
        filas.append(
            {
                "file_name": path.name,
                "suffix": path.suffix.lower(),
                "bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
            }
        )
    write_csv(ruta_salida, filas)
    upload_table_outputs_to_s3(configuracion, ruta_salida, f"{configuracion.s3_silver_prefix}/dataestur/dataestur_inventory")
    return [f"processed Dataestur inventory with {len(filas)} files -> {ruta_salida}"]


def process_dataestur_hotel_occupancy(configuracion: Settings, dry_run: bool) -> list[str]:
    ruta_entrada = latest_dataestur_hotel_file()
    ruta_salida = PROCESSED_DIR / "silver" / "dataestur_hotel_occupancy_by_province.csv"
    if dry_run:
        estado = f"from {ruta_entrada}" if ruta_entrada else "missing raw hotel occupancy file"
        return [f"DRY-RUN process Dataestur hotel occupancy ({estado}) -> {ruta_salida}"]
    if ruta_entrada is None:
        return ["skipped Dataestur hotel occupancy: raw hotel occupancy file is missing"]

    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install Dataestur processing dependencies with `pip install pandas openpyxl`.") from exc

    datos = pd.read_excel(ruta_entrada)
    datos = datos[datos["LUGAR_RESIDENCIA"].astype(str).str.strip().eq("Total")].copy()
    filas: list[dict[str, Any]] = []
    for _, elemento in datos.iterrows():
        anio = int(elemento["AÑO"])
        mes = int(elemento["MES"])
        filas.append(
            {
                "province": normalize_dataestur_province(elemento["PROVINCIA"]),
                "year": anio,
                "month": mes,
                "year_month": f"{anio:04d}-{mes:02d}",
                "ccaa": elemento.get("CCAA", ""),
                "hotel_travelers": clean_number(elemento.get("VIAJEROS")),
                "hotel_overnights": clean_number(elemento.get("PERNOCTACIONES")),
                "hotel_avg_stay": clean_number(elemento.get("ESTANCIA_MEDIA")),
                "hotel_establishments_estimated": clean_number(elemento.get("ESTABLECIMIENTOS_ESTIMADOS")),
                "hotel_rooms_estimated": clean_number(elemento.get("HABITACIONES_ESTIMADAS")),
                "hotel_beds_estimated": clean_number(elemento.get("PLAZAS_ESTIMADAS")),
                "hotel_occupancy_rate": clean_number(elemento.get("GRADO_OCUPA_PLAZAS")),
                "hotel_weekend_occupancy_rate": clean_number(elemento.get("GRADO_OCUPA_PLAZAS_FIN_SEMANA")),
                "hotel_room_occupancy_rate": clean_number(elemento.get("GRADO_OCUPA_POR_HABITACIONES")),
                "hotel_staff": clean_number(elemento.get("PERSONAL_EMPLEADO")),
                "source_file": ruta_entrada.name,
            }
        )

    filas = sorted(filas, key=lambda fila: (fila["province"], fila["year_month"]))
    write_csv(ruta_salida, filas)
    maybe_write_parquet(ruta_salida.with_suffix(".parquet"), filas)
    upload_table_outputs_to_s3(
        configuracion,
        ruta_salida,
        f"{configuracion.s3_silver_prefix}/dataestur/dataestur_hotel_occupancy_by_province",
    )
    return [f"processed Dataestur hotel occupancy with {len(filas)} rows -> {ruta_salida}"]


def latest_dataestur_hotel_file() -> Path | None:
    candidates = sorted((RAW_DIR / "dataestur" / "original").glob("hotel_occupancy_by_province*.xlsx"))
    return candidates[-1] if candidates else None


def process_holidays(configuracion: Settings, dry_run: bool) -> list[str]:
    ruta_entrada = RAW_DIR / "holidays" / "original" / (
        f"spanish_holidays_{configuracion.holidays_from_year}_{configuracion.holidays_to_year}.csv"
    )
    ruta_salida = PROCESSED_DIR / "silver" / "holidays_calendar.csv"
    if dry_run:
        existe = "exists" if ruta_entrada.exists() else "missing"
        return [f"DRY-RUN process Spanish holidays calendar ({existe}) -> {ruta_salida}"]
    if not ruta_entrada.exists():
        filas = build_holiday_rows(configuracion)
        ruta_entrada.parent.mkdir(parents=True, exist_ok=True)
        write_csv(ruta_entrada, filas)
    filas = read_csv_dicts(ruta_entrada)
    enriquecidas: list[dict[str, Any]] = []
    for fila in filas:
        dia = datetime.fromisoformat(fila["date"])
        enriquecidas.append(
            {
                **fila,
                "year": dia.year,
                "month": dia.month,
                "year_month": fila["date"][:7],
                "day_of_week": dia.weekday(),
                "is_weekend": dia.weekday() >= 5,
            }
        )
    write_csv(ruta_salida, enriquecidas)
    maybe_write_parquet(ruta_salida.with_suffix(".parquet"), enriquecidas)
    upload_table_outputs_to_s3(configuracion, ruta_salida, f"{configuracion.s3_silver_prefix}/holidays/holidays_calendar")
    return [f"processed Spanish holidays calendar with {len(enriquecidas)} rows -> {ruta_salida}"]


def process_aena(configuracion: Settings, dry_run: bool) -> list[str]:
    archivos = sorted((RAW_DIR / "aena").glob("*.xls")) + sorted((RAW_DIR / "aena").glob("*.xlsx"))
    ruta_salida = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic.csv"
    ruta_salida_provincia = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic_by_province.csv"
    if dry_run:
        return [f"DRY-RUN process {len(archivos)} AENA Excel files -> {ruta_salida}"]
    filas: list[dict[str, Any]] = []
    for path in archivos:
        filas.extend(parse_aena_file(path))
    write_csv(ruta_salida, filas)
    maybe_write_parquet(ruta_salida.with_suffix(".parquet"), filas)
    filas_provincia = aggregate_aena_by_province(filas)
    write_csv(ruta_salida_provincia, filas_provincia)
    maybe_write_parquet(ruta_salida_provincia.with_suffix(".parquet"), filas_provincia)
    upload_table_outputs_to_s3(configuracion, ruta_salida, f"{configuracion.s3_silver_prefix}/aena/aena_monthly_air_traffic")
    upload_table_outputs_to_s3(
        configuracion,
        ruta_salida_provincia,
        f"{configuracion.s3_silver_prefix}/aena/aena_monthly_air_traffic_by_province",
    )
    return [
        f"processed AENA airport-month table with {len(filas)} rows -> {ruta_salida}",
        f"processed AENA province-month table with {len(filas_provincia)} rows -> {ruta_salida_provincia}",
    ]


def parse_aena_file(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install AENA processing dependencies with `pip install pandas xlrd openpyxl`.") from exc

    anio, mes = parse_aena_file_date(path)
    nombre_hoja, datos, fila_titulo = find_aena_data_sheet(path, pd)
    pares = aena_block_pairs(datos, fila_titulo + 1)
    metricas: dict[str, dict[str, int]] = {}
    nombres_visibles: dict[str, str] = {}
    for metrica, (name_col, columna_total) in zip(("passengers", "operations", "cargo_kg"), pares):
        bloque = extract_aena_metric_block(datos, fila_titulo, name_col, columna_total)
        metricas[metrica] = bloque
        for nombre_normalizado, valor in bloque.items():
            if valor is not None:
                nombres_visibles.setdefault(nombre_normalizado, nombre_normalizado.title())

    aeropuertos = sorted(set().union(*(set(bloque) for bloque in metricas.values())))
    mapeo_faltante = sorted(aeropuerto for aeropuerto in aeropuertos if aeropuerto not in AENA_AIRPORT_PROVINCES)
    if mapeo_faltante:
        raise ValueError(f"Missing AENA airport province mapping: {', '.join(mapeo_faltante)}")

    filas = []
    for aeropuerto in aeropuertos:
        filas.append(
            {
                "year": anio,
                "month": mes,
                "year_month": f"{anio:04d}-{mes:02d}",
                "airport_name": nombres_visibles.get(aeropuerto, aeropuerto.title()),
                "airport_normalized": aeropuerto,
                "province": AENA_AIRPORT_PROVINCES[aeropuerto],
                "passengers": metricas.get("passengers", {}).get(aeropuerto, 0),
                "operations": metricas.get("operations", {}).get(aeropuerto, 0),
                "cargo_kg": metricas.get("cargo_kg", {}).get(aeropuerto, 0),
                "source_file": path.name,
                "source_sheet": nombre_hoja,
            }
        )
    return filas


def parse_aena_file_date(path: Path) -> tuple[int, int]:
    month_match = re.match(r"(\d{2})[._]", path.name)
    year_match = re.search(r"(20\d{2})", path.name)
    if not month_match or not year_match:
        raise ValueError(f"Cannot parse AENA month/year from file name: {path.name}")
    return int(year_match.group(1)), int(month_match.group(1))


def find_aena_data_sheet(path: Path, pd):
    libro = pd.ExcelFile(path)
    for nombre_hoja in libro.sheet_names:
        datos = pd.read_excel(path, header=None, sheet_name=nombre_hoja)
        fila_maxima = min(20, len(datos) - 2)
        for indice_fila in range(fila_maxima):
            texto_fila = " ".join(normalize_text(datos.iat[indice_fila, col]) for col in range(datos.shape[1]))
            texto_fila_siguiente = " ".join(
                normalize_text(datos.iat[indice_fila + 1, col]) for col in range(datos.shape[1])
            )
            if (
                "PASAJEROS" in texto_fila
                and "OPERACIONES" in texto_fila
                and "MERCANCIA" in texto_fila
                and "AEROPUERTOS" in texto_fila_siguiente
                and "TOTAL" in texto_fila_siguiente
            ):
                return nombre_hoja, datos, indice_fila
    raise ValueError(f"No AENA data table found in {path.name}")


def aena_block_pairs(datos, fila_cabecera: int) -> list[tuple[int, int]]:
    columnas_aeropuerto = [
        col for col in range(datos.shape[1]) if "AEROPUERTOS" in normalize_text(datos.iat[fila_cabecera, col])
    ]
    columnas_total = [
        col for col in range(datos.shape[1]) if normalize_text(datos.iat[fila_cabecera, col]) == "TOTAL"
    ]
    if len(columnas_aeropuerto) != 3 or len(columnas_total) < 3:
        raise ValueError(f"Unexpected AENA header layout: airports={columnas_aeropuerto}, totals={columnas_total}")
    pares = []
    for columna_aeropuerto in columnas_aeropuerto:
        columna_total = next((col for col in columnas_total if col > columna_aeropuerto), None)
        if columna_total is None:
            raise ValueError(f"No total column found after AENA airport column {columna_aeropuerto}")
        pares.append((columna_aeropuerto, columna_total))
    return pares


def extract_aena_metric_block(datos, fila_titulo: int, name_col: int, columna_total: int) -> dict[str, int]:
    filas_total = [
        fila
        for fila in range(fila_titulo + 3, len(datos))
        if normalize_text(datos.iat[fila, name_col]).startswith("TOTAL")
    ]
    if not filas_total:
        raise ValueError("No total row found in AENA metric block")
    fila_fin = filas_total[0]
    valores: dict[str, int] = {}
    for fila in range(fila_titulo + 3, fila_fin):
        aeropuerto = normalize_airport_name(datos.iat[fila, name_col])
        if not aeropuerto:
            continue
        valor_bruto = datos.iat[fila, columna_total]
        valores[aeropuerto] = int(float(valor_bruto)) if valor_bruto == valor_bruto else 0
    return valores


def aggregate_aena_by_province(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agrupados: dict[tuple[str, str], dict[str, Any]] = {}
    for fila in filas:
        clave = (fila["province"], fila["year_month"])
        elemento = agrupados.setdefault(
            clave,
            {
                "province": fila["province"],
                "year_month": fila["year_month"],
                "passengers": 0,
                "operations": 0,
                "cargo_kg": 0,
                "airport_count": 0,
            },
        )
        elemento["passengers"] += int(fila["passengers"])
        elemento["operations"] += int(fila["operations"])
        elemento["cargo_kg"] += int(fila["cargo_kg"])
        elemento["airport_count"] += 1
    return sorted(agrupados.values(), key=lambda elemento: (elemento["province"], elemento["year_month"]))


def write_gold_feature_table(configuracion: Settings) -> list[str]:
    ruta_clima = PROCESSED_DIR / "silver" / "open_meteo_monthly.csv"
    ruta_salida = PROCESSED_DIR / "gold" / "tourism_weather_monthly_features.csv"
    if not ruta_clima.exists():
        return ["skipped gold feature table: Open-Meteo silver table is missing"]
    filas = read_csv_dicts(ruta_clima)
    conteos_festivos = monthly_holiday_counts()
    aena_por_provincia = monthly_aena_by_province()
    ocupacion_hotelera = monthly_hotel_occupancy_by_province()
    for fila in filas:
        codigo_region = PROVINCE_REGION_CODES.get(fila["province"], "")
        festivos_nacionales = conteos_festivos.get((fila["year_month"], "ES"), 0)
        festivos_regionales = conteos_festivos.get((fila["year_month"], codigo_region), 0)
        datos_aena = aena_por_provincia.get((fila["province"], fila["year_month"]), {})
        datos_hotel = ocupacion_hotelera.get((fila["province"], fila["year_month"]), {})
        fila["region_code"] = codigo_region
        fila["national_holiday_count"] = festivos_nacionales
        fila["regional_holiday_count"] = festivos_regionales
        fila["total_holiday_count"] = festivos_nacionales + festivos_regionales
        fila["aena_passengers"] = datos_aena.get("passengers", 0)
        fila["aena_operations"] = datos_aena.get("operations", 0)
        fila["aena_cargo_kg"] = datos_aena.get("cargo_kg", 0)
        fila["aena_airport_count"] = datos_aena.get("airport_count", 0)
        fila["hotel_travelers"] = datos_hotel.get("hotel_travelers", "")
        fila["hotel_overnights"] = datos_hotel.get("hotel_overnights", "")
        fila["hotel_avg_stay"] = datos_hotel.get("hotel_avg_stay", "")
        fila["hotel_establishments_estimated"] = datos_hotel.get("hotel_establishments_estimated", "")
        fila["hotel_rooms_estimated"] = datos_hotel.get("hotel_rooms_estimated", "")
        fila["hotel_beds_estimated"] = datos_hotel.get("hotel_beds_estimated", "")
        fila["hotel_occupancy_rate"] = datos_hotel.get("hotel_occupancy_rate", "")
        fila["hotel_weekend_occupancy_rate"] = datos_hotel.get("hotel_weekend_occupancy_rate", "")
        fila["hotel_room_occupancy_rate"] = datos_hotel.get("hotel_room_occupancy_rate", "")
        fila["hotel_staff"] = datos_hotel.get("hotel_staff", "")
        fila["target_available"] = bool(datos_hotel.get("hotel_overnights"))
        fila["feature_source"] = "open_meteo_monthly+holidays+aena+dataestur_hotel"
    write_csv(ruta_salida, filas)
    maybe_write_parquet(ruta_salida.with_suffix(".parquet"), filas)
    upload_table_outputs_to_s3(configuracion, ruta_salida, f"{configuracion.s3_gold_prefix}/tourism_weather_monthly_features")
    return [f"wrote gold feature table with {len(filas)} rows -> {ruta_salida}"]


def monthly_holiday_counts() -> dict[tuple[str, str], int]:
    holidays_path = PROCESSED_DIR / "silver" / "holidays_calendar.csv"
    if not holidays_path.exists():
        return {}
    conteos: dict[tuple[str, str], int] = {}
    for fila in read_csv_dicts(holidays_path):
        if fila.get("scope") not in {"national", "regional"}:
            continue
        clave = (fila["year_month"], fila["region_code"])
        conteos[clave] = conteos.get(clave, 0) + 1
    return conteos


def monthly_aena_by_province() -> dict[tuple[str, str], dict[str, int]]:
    path = PROCESSED_DIR / "silver" / "aena_monthly_air_traffic_by_province.csv"
    if not path.exists():
        return {}
    valores: dict[tuple[str, str], dict[str, int]] = {}
    for fila in read_csv_dicts(path):
        valores[(fila["province"], fila["year_month"])] = {
            "passengers": int(float(fila["passengers"] or 0)),
            "operations": int(float(fila["operations"] or 0)),
            "cargo_kg": int(float(fila["cargo_kg"] or 0)),
            "airport_count": int(float(fila["airport_count"] or 0)),
        }
    return valores


def monthly_hotel_occupancy_by_province() -> dict[tuple[str, str], dict[str, str]]:
    path = PROCESSED_DIR / "silver" / "dataestur_hotel_occupancy_by_province.csv"
    if not path.exists():
        return {}
    valores: dict[tuple[str, str], dict[str, str]] = {}
    for fila in read_csv_dicts(path):
        valores[(fila["province"], fila["year_month"])] = fila
    return valores


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


def catalog_athena_tables(configuracion: Settings, dry_run: bool) -> list[str]:
    if not configuracion.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is required to catalog Athena tables.")
    if not configuracion.athena_results_s3_uri:
        raise ValueError("ATHENA_RESULTS_S3_URI is required to run Athena DDL.")
    acciones = [
        f"ensure Glue database exists: {configuracion.glue_database}",
        f"create/update {len(ATHENA_PARQUET_TABLES)} Athena external Parquet tables",
    ]
    if dry_run:
        return [f"DRY-RUN {action}" for action in acciones] + [
            f"DRY-RUN table {name} -> s3://{configuracion.s3_bucket_name}/{ubicacion}"
            for name, (ubicacion, _columns) in ATHENA_PARQUET_TABLES.items()
        ]

    ensure_glue_database(configuracion)
    ensure_athena_workgroup(configuracion)
    for nombre_tabla, (ubicacion, columnas) in ATHENA_PARQUET_TABLES.items():
        consulta = athena_create_parquet_table_sql(configuracion, nombre_tabla, ubicacion, columnas)
        run_athena_query(configuracion, consulta)
        acciones.append(f"cataloged Athena table {configuracion.glue_database}.{nombre_tabla}")
    consulta_validacion = (
        "SELECT COUNT(*) AS rows, COUNT(hotel_overnights) AS target_rows "
        "FROM gold_tourism_weather_monthly_features"
    )
    id_consulta = run_athena_query(configuracion, consulta_validacion)
    acciones.append(f"validated gold table with Athena query {id_consulta}")
    return acciones


def athena_create_parquet_table_sql(
    configuracion: Settings,
    nombre_tabla: str,
    ubicacion: str,
    columnas: list[tuple[str, str]],
) -> str:
    sql_columnas = ",\n  ".join(f"`{name}` {athena_type}" for name, athena_type in columnas)
    ubicacion_s3 = f"s3://{configuracion.s3_bucket_name}/{ubicacion}"
    return f"""
CREATE EXTERNAL TABLE IF NOT EXISTS `{configuracion.glue_database}`.`{nombre_tabla}` (
  {sql_columnas}
)
STORED AS PARQUET
LOCATION '{ubicacion_s3}'
TBLPROPERTIES ('parquet.compression'='SNAPPY')
"""


def run_athena_query(configuracion: Settings, consulta: str) -> str:
    cliente_athena = aws_client(configuracion, "athena")
    respuesta = cliente_athena.start_query_execution(
        QueryString=consulta,
        QueryExecutionContext={"Database": configuracion.glue_database},
        WorkGroup=configuracion.athena_workgroup,
        ResultConfiguration={"OutputLocation": configuracion.athena_results_s3_uri},
    )
    id_consulta = respuesta["QueryExecutionId"]
    deadline = time.monotonic() + ATHENA_QUERY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        ejecucion = cliente_athena.get_query_execution(QueryExecutionId=id_consulta)["QueryExecution"]
        estado_consulta = ejecucion["Status"]["State"]
        if estado_consulta == "SUCCEEDED":
            return id_consulta
        if estado_consulta in {"FAILED", "CANCELLED"}:
            motivo = ejecucion["Status"].get("StateChangeReason", "unknown")
            raise RuntimeError(f"Athena query {id_consulta} {estado_consulta}: {motivo}")
        time.sleep(ATHENA_QUERY_POLL_SECONDS)
    raise TimeoutError(f"Athena query {id_consulta} did not finish in time.")


def normalize_text(valor: Any) -> str:
    if valor is None or valor != valor:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip().upper())
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto).strip()


def normalize_airport_name(valor: Any) -> str:
    texto = normalize_text(valor)
    if not texto:
        return ""
    texto = re.sub(r"\s*\(\*+\)\s*$", "", texto)
    texto = re.sub(r"\s*/\s*", "-", texto)
    texto = re.sub(r"\s*-\s*", "-", texto)
    texto = re.sub(r"-{2,}", "-", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalize_dataestur_province(valor: Any) -> str:
    texto = normalize_text(valor)
    if not texto:
        return ""
    if texto in DATAESTUR_PROVINCE_ALIASES:
        return DATAESTUR_PROVINCE_ALIASES[texto]
    for province in PROVINCE_REGION_CODES:
        if normalize_text(province) == texto:
            return province
    return str(valor).strip()


def clean_number(valor: Any) -> int | float | None:
    if valor is None or valor != valor:
        return None
    number = float(valor)
    if number.is_integer():
        return int(number)
    return round(number, 4)


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as manejador:
        return list(csv.DictReader(manejador))


def write_csv(path: Path, filas: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        path.write_text("", encoding="utf-8")
        return
    nombres_campos = list(filas[0].keys())
    with path.open("w", encoding="utf-8", newline="") as manejador:
        escritor = csv.DictWriter(manejador, fieldnames=nombres_campos)
        escritor.writeheader()
        escritor.writerows(filas)


def maybe_write_parquet(path: Path, filas: list[dict[str, Any]]) -> None:
    if not filas:
        return
    try:
        import pandas as pd
    except ImportError:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tabla = pd.DataFrame(filas)
    for columna in tabla.columns:
        if columna in PARQUET_STRING_COLUMNS:
            continue
        if columna == "target_available":
            tabla[columna] = tabla[columna].map(
                lambda valor: valor
                if isinstance(valor, bool)
                else str(valor).strip().lower() in {"true", "1", "yes"}
            )
            continue
        convertida = pd.to_numeric(tabla[columna], errors="coerce")
        if convertida.notna().sum() or tabla[columna].isna().all():
            tabla[columna] = convertida
    tabla.to_parquet(path, index=False)


def safe_stem(valor: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", valor).strip("_").lower()


def main() -> int:
    global SKIP_S3_UPLOAD
    argumentos_cli = parse_args()
    SKIP_S3_UPLOAD = argumentos_cli.skip_s3_upload
    configure_logging(argumentos_cli.log_level)
    configuracion = get_settings()

    if argumentos_cli.list_dataestur:
        for endpoint, name in DATAESTUR_ENDPOINTS.items():
            print(f"- {endpoint}: {name}")
        return 0
    if argumentos_cli.check_config:
        print_config_check(configuracion)
        return 0
    if argumentos_cli.ingest and argumentos_cli.skip_ingest:
        raise SystemExit("Use either --ingest or --skip-ingest, not both.")

    ejecutar_todo = not any((argumentos_cli.deploy, argumentos_cli.ingest, argumentos_cli.process, argumentos_cli.catalog))
    faltantes = []
    if not argumentos_cli.dry_run and (argumentos_cli.deploy or ejecutar_todo):
        faltantes.extend(configuracion.required_aws_values)
    if faltantes:
        raise SystemExit(f"Missing required configuration: {', '.join(dict.fromkeys(faltantes))}")

    inicio_ejecucion = time.perf_counter()
    acciones: list[str] = []
    if argumentos_cli.deploy or ejecutar_todo:
        LOGGER.info("Deploy phase started")
        acciones.extend(provision(configuracion, argumentos_cli.dry_run))
    if argumentos_cli.ingest or (ejecutar_todo and not argumentos_cli.skip_ingest):
        LOGGER.info("Ingestion phase started")
        acciones.extend(ingest(configuracion, argumentos_cli))
    if argumentos_cli.process or ejecutar_todo:
        LOGGER.info("Processing phase started")
        acciones.extend(process(configuracion, argumentos_cli.dry_run, argumentos_cli.source))
    if argumentos_cli.catalog:
        LOGGER.info("Catalog phase started")
        acciones.extend(catalog_athena_tables(configuracion, argumentos_cli.dry_run))

    for action in acciones:
        print(f"- {action}")
    LOGGER.info("Pipeline finished in %.1fs", time.perf_counter() - inicio_ejecucion)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        LOGGER.exception("Pipeline failed")
        raise
