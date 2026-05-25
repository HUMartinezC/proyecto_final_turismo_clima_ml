# Arquitectura AWS

## Vista general

La arquitectura usa S3 como repositorio unico y separa las cargas segun su naturaleza:

- S3 guarda todo el data lake en capas.
- DocumentDB se reserva para conservar payloads JSON de APIs externas cuando sea necesario para trazabilidad.
- RDS MariaDB guarda tablas estructuradas finales y metricas de modelos en entorno de pruebas.
- Glue cataloga y transforma datos.
- Athena permite EDA SQL sin mover datos.
- Lambda automatiza ingestas y ejecuciones programadas en fases posteriores.
- Amazon MSK cubre el requisito Kafka para eventos en tiempo real en fases posteriores.

## Capas del data lake

```text
s3://bucket/bronze/   Datos originales de aterrizaje y manifests
s3://bucket/silver/   Datos limpios con tipos consistentes
s3://bucket/gold/     Tabla final de features para EDA y ML
```

## Flujo

1. El script unico invoca conectores de Dataestur, Open-Meteo y festivos. AENA se incorpora desde Excel descargados manualmente en `datasets/raw/aena/`.
2. Los datos originales se guardan en S3 bronze; en local, los originales descargados o generados se conservan en `datasets/raw/`.
3. El procesamiento local genera tablas silver y gold en CSV/Parquet.
4. Glue Crawlers podran actualizar el Data Catalog sobre S3.
5. Athena consulta tablas silver/gold para EDA y validación.
6. La tabla gold se usa para entrenamiento local o en SageMaker.
7. Métricas y predicciones agregadas se pueden publicar en RDS MariaDB.
8. DocumentDB, Lambda y MSK quedan definidos como componentes de arquitectura para ampliar automatizacion, trazabilidad y tiempo real en fases posteriores.

## Particionado recomendado

- Turismo: `source`, `year`, `month`, `region`.
- Clima: `source`, `year`, `month`, `province`.
- Movilidad: `source`, `year`, `month`, `airport`, `station` o `province`, segun la fuente.
- Gold: `year`, `month`, `region`.

## Script unico

El punto de entrada es `scripts/run_pipeline.py`.

```bash
python scripts/run_pipeline.py --dry-run
python scripts/run_pipeline.py
```

La ejecución sin argumentos intenta siempre el flujo completo: despliegue, ingesta y procesamiento. Las operaciones de despliegue deben ser idempotentes: si el bucket, prefijos o base de datos de Glue ya existen, se reutilizan.

El modo `dry-run` permite demostrar la orquestacion sin consumir recursos AWS.

Para AENA, el script no descarga los informes desde la web: procesa los Excel ya descargados manualmente en `datasets/raw/aena/` y genera las tablas silver por aeropuerto y provincia.
