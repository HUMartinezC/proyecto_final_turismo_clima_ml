# Decisiones tecnicas

## Tecnologias obligatorias

| Requisito | Eleccion |
|---|---|
| ETL/ELT | AWS Glue para jobs ETL y Data Catalog; Athena para consulta |
| S3 | Data lake principal por capas |
| RDS | MariaDB para entorno de pruebas, tablas estructuradas finales y metricas |
| Lambda | Automatizacion de ingesta y disparo de jobs |
| NoSQL | Amazon DocumentDB para respuestas JSON semiestructuradas |
| Kafka | Amazon MSK como Kafka gestionado en AWS |
| boto3 | Cliente AWS usado directamente desde `scripts/run_pipeline.py` |

## Tecnologias utiles

- Parquet + Snappy: formato eficiente para Athena y Glue.
- pandas/pyarrow: procesamiento local y serializacion.
- scikit-learn/XGBoost/Gradio: quedan como extension futura si se implementa entrenamiento y demo.
- SageMaker: opcional si se quiere entrenar completamente dentro de AWS.

## Por que estas fuentes y no mas

El objetivo no es acumular fuentes, sino construir una union defendible. Dataestur y AEMET explican directamente demanda y clima; festivos explican estacionalidad; AENA anade movilidad si el tiempo del proyecto lo permite. El resto queda como ampliacion.

## Riesgos

- Cobertura temporal desigual entre turismo y clima.
- Granularidad distinta entre estaciones meteorologicas, provincias y CCAA.
- Necesidad de mapear estaciones AEMET a regiones turisticas.
- APIs con limites, cambios de esquema o autenticacion.
- MariaDB publico en RDS facilita pruebas, pero no debe usarse asi en produccion.

## Mitigacion

- Definir una tabla de correspondencias `region_station_mapping`.
- Mantener los datos originales inmutables en la capa bronze de S3.
- Versionar datasets procesados por fecha de ejecucion.
- Usar Athena para validar conteos y nulos antes del entrenamiento.
- Restringir el security group de MariaDB a una IP concreta cuando deje de ser una prueba.
