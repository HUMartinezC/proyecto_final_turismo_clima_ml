# Arquitectura AWS

## Vista general

La arquitectura usa S3 como repositorio unico y separa las cargas segun su naturaleza:

- S3 guarda todo el data lake en capas.
- DocumentDB conserva payloads JSON de APIs externas para trazabilidad.
- RDS MariaDB guarda tablas estructuradas finales y metricas de modelos en entorno de pruebas.
- Glue cataloga y transforma datos.
- Athena permite EDA SQL sin mover datos.
- Lambda automatiza ingestas y ejecuciones programadas.
- Amazon MSK cubre el requisito Kafka para eventos en tiempo real.

## Capas del data lake

```text
s3://bucket/bronze/   Datos originales de aterrizaje y manifests
s3://bucket/silver/   Datos limpios con tipos consistentes
s3://bucket/gold/     Tabla final de features para EDA y ML
```

## Flujo

1. Lambda o el script unico invoca conectores de Dataestur, AEMET, festivos y AENA.
2. Los datos originales se guardan en S3 bronze.
3. Los JSON completos de APIs se replican en DocumentDB cuando conviene conservar estructura semiestructurada.
4. Glue Crawlers actualizan el Data Catalog.
5. Glue Jobs transforman bronze/silver/gold y generan Parquet particionado.
6. Athena consulta tablas silver/gold para EDA y validacion.
7. La tabla gold se usa para entrenamiento local o en SageMaker.
8. Metricas y predicciones agregadas se pueden publicar en RDS MariaDB.
9. MSK recibe eventos nuevos, por ejemplo observaciones climaticas o eventos turisticos, para futuras actualizaciones casi en tiempo real.

## Particionado recomendado

- Turismo: `source`, `year`, `month`, `region`.
- Clima: `source`, `year`, `month`, `station`.
- Gold: `year`, `month`, `region`.

## Script unico

El punto de entrada es `scripts/run_pipeline.py`.

```bash
python scripts/run_pipeline.py --dry-run
python scripts/run_pipeline.py
```

La ejecucion sin argumentos intenta siempre el flujo completo: despliegue, ingesta y procesamiento. Las operaciones de despliegue deben ser idempotentes: si el bucket, prefijos o base de datos de Glue ya existen, se reutilizan.

El modo `dry-run` permite demostrar la orquestacion sin consumir recursos AWS.
