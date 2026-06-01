# Arquitectura

## Vista general

La arquitectura combina ejecucion local reproducible con almacenamiento y consulta en AWS:

- S3 guarda el data lake por capas.
- Glue Data Catalog registra las tablas externas.
- Athena consulta los Parquet de S3 con SQL.
- RDS MariaDB queda disponible para resultados estructurados y pruebas relacionales.
- Lambda puede crearse si se configura `LAMBDA_ROLE_ARN`.
- El procesamiento ETL se ejecuta con Python desde `scripts/run_pipeline.py`.

## Capas del data lake

```text
s3://bucket/bronze/   Datos originales y manifests
s3://bucket/silver/   Datos normalizados por fuente
s3://bucket/gold/     Tabla integrada de features para EDA y ML
```

En local se usa:

```text
datasets/raw/              Originales locales y manifests
datasets/processed/silver/ Tablas normalizadas reproducibles
datasets/processed/gold/   Tabla final de features
```

## Flujo

1. `scripts/run_pipeline.py` ingiere Dataestur, Open-Meteo y festivos.
2. Los Excel mensuales de AENA se colocan manualmente en `datasets/raw/aena/`.
3. Los originales se guardan en `datasets/raw/` y, si procede, en `s3://bucket/bronze/`.
4. El procesamiento genera tablas silver en CSV y Parquet.
5. La capa gold integra turismo, clima, calendario y movilidad por `province + year_month`.
6. Los Parquet se publican en S3 con rutas separadas por tabla y formato.
7. `--catalog` crea o actualiza tablas externas en Glue Data Catalog mediante Athena DDL.
8. Los notebooks consumen la tabla gold desde local o desde S3.

## Tablas catalogadas

```text
silver_open_meteo_monthly
silver_dataestur_hotel_occupancy_by_province
silver_holidays_calendar
silver_aena_monthly_air_traffic
silver_aena_monthly_air_traffic_by_province
gold_tourism_weather_monthly_features
```

## Rutas principales en S3

```text
bronze/dataestur/
bronze/open_meteo/
bronze/holidays/
bronze/aena/
silver/open_meteo/open_meteo_monthly/
silver/dataestur/dataestur_hotel_occupancy_by_province/
silver/holidays/holidays_calendar/
silver/aena/aena_monthly_air_traffic/
silver/aena/aena_monthly_air_traffic_by_province/
gold/tourism_weather_monthly_features/
```

Cada salida procesada puede tener subcarpetas `csv/` y `parquet/`.

## Comandos habituales

```bash
python scripts/run_pipeline.py --dry-run
python scripts/run_pipeline.py
python scripts/run_pipeline.py --skip-ingest
python scripts/run_pipeline.py --process --skip-s3-upload
python scripts/run_pipeline.py --catalog
```

La ejecucion sin argumentos intenta despliegue, ingesta y procesamiento. Las ejecuciones parciales permiten validar o regenerar componentes concretos sin repetir descargas.
