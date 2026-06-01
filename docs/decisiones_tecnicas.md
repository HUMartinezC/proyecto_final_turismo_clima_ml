# Decisiones tecnicas

## Tecnologias usadas

| Necesidad | Eleccion |
|---|---|
| Data lake | Amazon S3 por capas `bronze`, `silver`, `gold` |
| Catalogo | AWS Glue Data Catalog |
| Consulta SQL | Amazon Athena sobre Parquet en S3 |
| Procesamiento | Python con pandas, numpy y pyarrow |
| Automatizacion AWS | `boto3` desde `scripts/run_pipeline.py` |
| Base relacional | Amazon RDS MariaDB para pruebas y resultados estructurados |
| Calendario | Paquete `holidays` |
| Modelado | scikit-learn y XGBoost |
| Visualizacion | matplotlib y seaborn |

## Cobertura tecnologica

En este proyecto se cubre con Athena y Glue Data Catalog: los datos procesados se publican en S3 en formato Parquet y se registran como tablas externas consultables por SQL.

La propuesta de estructura incluye una carpeta `spark/` como ejemplo orientativo, pero el volumen y la naturaleza mensual de los datos no justifican introducir un motor distribuido.

El procesamiento en tiempo real con Kafka no encaja de forma natural con las fuentes integradas. Dataestur, Open-Meteo, festivos y AENA son fuentes historicas o batch: se descargan por rango temporal, se normalizan y se agregan a nivel mensual. No existe un flujo de eventos continuo que aporte valor real al target `hotel_overnights`.

La alternativa tecnica seria generar eventos sinteticos de ingesta o publicar cada fila procesada como evento, pero eso no mejoraria el modelo ni la arquitectura de datos. Por este motivo, Kafka se documenta como tecnologia no implementada en el flujo actual.

DocumentDB se mantiene tambien como componente no implementado en el flujo actual. Las respuestas originales quedan conservadas en `datasets/raw/` y S3 bronze; esa estrategia cubre la trazabilidad de los JSON sin introducir una base NoSQL adicional que no se consulta en el analisis ni en el modelado.

## Decisiones de arquitectura

- El ETL se mantiene en Python para que el flujo sea reproducible en local y facil de trasladar a AWS.
- Glue se usa como catalogo, no como motor de jobs.
- Athena se usa para validar tablas publicadas en S3 sin mover datos.
- AENA se descarga manualmente porque el portal publica Excel mensuales y no ofrece una API estable equivalente.
- Open-Meteo se usa como fuente climatica principal porque no requiere API key y cubre todo el periodo por coordenadas.
- AEMET queda documentada como contraste oficial, pero no forma parte del flujo implementado.

## Por que estas fuentes

El objetivo es construir una union defendible, no acumular fuentes. Dataestur aporta el target, Open-Meteo explica condiciones climaticas, `holidays` introduce estacionalidad y AENA añade movilidad aeroportuaria.

La movilidad terrestre se mantiene como candidata porque podria mejorar la explicacion del turismo nacional y de proximidad. Solo tendria sentido incorporarla si aporta informacion mensual y territorial compatible con `province + year_month`.

## Riesgos

- Cobertura temporal desigual entre turismo, clima y movilidad.
- Granularidad distinta entre provincias, aeropuertos y comunidades autonomas.
- Errores de mapeo aeropuerto-provincia.
- Cambios de esquema o limites en APIs externas.
- Faltan datos de AENA si no se descargan todos los meses necesarios.
