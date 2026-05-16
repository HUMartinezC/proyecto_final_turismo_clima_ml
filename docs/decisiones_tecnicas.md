# Decisiones tecnicas

## Tecnologias obligatorias

| Requisito | Eleccion |
|---|---|
| ETL/ELT | AWS Glue para jobs ETL y Data Catalog; Athena para consulta |
| S3 | Data lake principal por capas |
| RDS | MariaDB para entorno de pruebas, tablas estructuradas finales y metricas |
| Lambda | Automatizacion de ingesta y disparo de jobs |
| NoSQL | Amazon DocumentDB para respuestas JSON semiestructuradas en fases posteriores |
| Kafka | Amazon MSK como Kafka gestionado en AWS en fases posteriores |
| boto3 | Cliente AWS usado directamente desde `scripts/run_pipeline.py` |

## Tecnologias utiles

- Parquet + Snappy: formato eficiente para Athena y Glue.
- pandas/pyarrow: procesamiento local y serializacion.
- holidays: generacion reproducible de calendario laboral sin depender de una API externa.
- scikit-learn/XGBoost/Gradio: quedan para entrenamiento y demo en fases posteriores.
- SageMaker: opcional si se quiere entrenar completamente dentro de AWS.

## Por que estas fuentes y no mas

El objetivo no es acumular fuentes, sino construir una unión defendible. Dataestur explica la demanda turística, Open-Meteo aporta clima reproducible, festivos explica estacionalidad y AENA añade movilidad aeroportuaria. La movilidad terrestre se contempla como ampliación porque puede explicar mejor turismo nacional y de proximidad, pero solo se incorporará si la fuente elegida permite una agregación mensual y territorial consistente. AEMET queda como contraste oficial opcional.

Los datos de AENA se descargan manualmente porque el portal publica informes mensuales en Excel y no ofrece una API estable equivalente a las otras fuentes. Esta decision reduce fragilidad: el script unico mantiene automatizado el procesamiento, normalizacion y subida a capas silver/gold, pero no depende de scraping ni de URLs cambiantes para obtener los Excel.

## Riesgos

- Cobertura temporal desigual entre turismo, clima y movilidad.
- Granularidad distinta entre provincias, aeropuertos y comunidades autonomas.
- Necesidad de mapear aeropuertos AENA a provincias.
- APIs con limites, cambios de esquema o autenticacion.
- Descargas manuales de AENA pueden introducir errores de cobertura si falta algun mes.
- Las fuentes de movilidad terrestre pueden no tener el detalle provincial o mensual necesario.
- MariaDB publico en RDS facilita pruebas, pero no debe usarse asi en produccion.

## Mitigacion

- Definir tablas de correspondencias, especialmente aeropuerto-provincia para AENA.
- Mantener los datos originales inmutables en la capa bronze de S3.
- Versionar datasets procesados por fecha de ejecución.
- Usar Athena para validar conteos y nulos antes del entrenamiento.
- Validar que `datasets/raw/aena/` contiene 12 ficheros por año antes de procesar movilidad.
- Evaluar la movilidad terrestre primero como fuente candidata y descartarla si no mejora la cobertura frente a AENA.
- Restringir el security group de MariaDB a una IP concreta cuando deje de ser una prueba.
