# Tourism Weather ML

Proyecto de Machine Learning para estimar la demanda turística en España a partir de datos de turismo, clima, calendario y movilidad.

## Problema elegido

Prediccion supervisada de ocupacion/pernoctaciones hoteleras por provincia o comunidad autonoma y mes. El objetivo es anticipar demanda turistica y explicar el impacto del clima y la estacionalidad.

## Stack principal implementado

- AWS S3 como data lake por capas: `bronze`, `silver`, `gold`.
- AWS Glue para catalogo, crawlers y jobs ETL.
- Amazon Athena para consultas SQL sobre S3.
- Amazon RDS MariaDB para datasets estructurados finales y metricas de entrenamiento en entorno de pruebas.
- AWS Lambda para automatizaciones de ingesta y disparo de jobs.
- Python, boto3, pandas, holidays, pyarrow y requests.

## Fuentes de datos elegidas

1. Dataestur: demanda turistica agregada, alojamientos, gasto y transporte.
2. Open-Meteo: clima historico diario reproducible por provincia.
3. Calendario laboral/festivos: estacionalidad, puentes y vacaciones.
4. AENA Open Data: movilidad aeroportuaria como proxy de demanda.

AEMET queda como fuente oficial española de contraste y solo se descarga si se pide explícitamente con `--source aemet`.

## Primeros pasos

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py --check-config
python scripts/run_pipeline.py --dry-run
```

`scripts/run_pipeline.py` es un ejecutable unico reproducible para todo el flujo. En un solo fichero carga `.env`, despliega recursos
basicos en AWS con `boto3`, ingiere Dataestur/Open-Meteo en `datasets/raw/` y
procesa los ficheros locales hacia `datasets/processed/silver/` y
`datasets/processed/gold/`. 

Para ejecutar contra AWS, configura `.env` y ejecuta:

```bash
python scripts/run_pipeline.py
```

Siempre se puede simular primero sin llamadas externas ni escrituras:

```bash
python scripts/run_pipeline.py --dry-run
```

Y si solo quieres regenerar las tablas locales a partir de los ficheros ya
descargados en `datasets/raw/`, sin subir nada a S3:

```bash
python scripts/run_pipeline.py --process --skip-s3-upload
```

Por defecto el script intenta el flujo completo: despliegue idempotente, ingesta y procesamiento. La ingesta por defecto usa Dataestur para turismo, Open-Meteo para clima, `holidays` para calendario laboral y los ficheros AENA locales para movilidad; AEMET queda fuera salvo ejecucion explicita con `--source aemet`. Si un recurso ya existe, se reutiliza. Las opciones `--deploy`, `--ingest`, `--process`, `--source` y `--dataestur-endpoint` quedan para depuracion o ejecuciones parciales.

## Dataestur

Dataestur publica una API en `https://www.dataestur.es/apidata/`. El OpenAPI usa como servidor `https://dataestur.azure-api.net/API-SEGITTUR-v1/`. El proyecto descarga por defecto una seleccion curada de endpoints:

- `EOH_PROV_DL`
- `EOH_CCAA_DL`
- `FRONTUR_DL`
- `ETR_DL`
- `EGATUR_DL`
- `AENA_DESTINOS_DL`
- `VALORES_CLIMATOLOGICOS_TEMPERATURA_DL`
- `VALORES_CLIMATOLOGICOS_PRECIPITACION_DL`

`IND_RENTABILIDAD_PROVINCIA_DL` queda como fuente manual porque Dataestur exige seleccionar provincia. Si se quiere incorporar rentabilidad hotelera, hay que copiar desde la interfaz una `Request URL` ya filtrada y ponerla en `DATAESTUR_EXTRA_REQUEST_URLS`.

Puedes ajustar la lista en `.env`:

```env
DATAESTUR_ENDPOINTS=EOH_PROV_DL,FRONTUR_DL,EGATUR_DL
DATAESTUR_FROM_YEAR=2015
DATAESTUR_FROM_MONTH=10
DATAESTUR_TO_YEAR=2024
DATAESTUR_TO_MONTH=12
DATAESTUR_EXTRA_REQUEST_URLS=rentabilidad_madrid=https://...
```

Para una consulta con filtros concretos:

1. Entra en la API de Dataestur.
2. Selecciona la fuente, por ejemplo `Ocupación alojamientos hoteleros`.
3. Pulsa `Pruébalo`, rellena filtros y pulsa `Execute`.
4. Copia el `Request URL` en `.env` como `DATAESTUR_EOH_REQUEST_URL`.
5. Ejecuta:

```bash
python scripts/run_pipeline.py --ingest --source dataestur
```

Prueba recomendada de una sola llamada:

```bash
python scripts/run_pipeline.py --ingest --source dataestur --dataestur-endpoint EOH_PROV_DL --dry-run
python scripts/run_pipeline.py --ingest --source dataestur --dataestur-endpoint EOH_PROV_DL
```

La ingesta guarda el fichero original local en `datasets/raw/dataestur/original/` y un manifest de trazabilidad en `datasets/raw/dataestur/landing_manifest/`. En S3 conserva la capa `bronze/dataestur/...`.

## AEMET OpenData opcional

AEMET requiere una API key gratuita en `AEMET_API_KEY`. Esta fuente no se ejecuta en el flujo por defecto; Open-Meteo es la fuente climatica principal. AEMET se reserva para contraste oficial y debe lanzarse explicitamente con `--source aemet`.

```env
AEMET_API_KEY=tu_api_key
AEMET_FROM_DATE=2015-10-01T00:00:00UTC
AEMET_TO_DATE=2024-12-31T00:00:00UTC
AEMET_STATIONS=8178D,8050X
AEMET_CHUNK_DAYS=15
AEMET_SKIP_EXISTING=true
```

Si `AEMET_STATIONS` queda vacio, se solicitan todas las estaciones para el rango configurado. Para evitar descargas grandes por accidente, si las fechas estan vacias solo se descarga el inventario. Los rangos largos se dividen automaticamente en bloques de `AEMET_CHUNK_DAYS`.

```bash
python scripts/run_pipeline.py --ingest --source aemet --dry-run
python scripts/run_pipeline.py --ingest --source aemet
```

La ingesta guarda los ficheros originales locales en `datasets/raw/aemet/original/` y un manifest de trazabilidad en `datasets/raw/aemet/landing_manifest/`.
Si una descarga historica se corta, puedes relanzar el comando: con `AEMET_SKIP_EXISTING=true` reutiliza los bloques ya descargados y continua con los que faltan.

## Festivos

Los festivos se generan localmente con el paquete Python `holidays`, sin depender de una API externa. El rango se configura en `.env`:

```env
HOLIDAYS_FROM_YEAR=2015
HOLIDAYS_TO_YEAR=2024
```

```bash
python scripts/run_pipeline.py --ingest --source holidays --dry-run
python scripts/run_pipeline.py --ingest --source holidays
python scripts/run_pipeline.py --process --source holidays
```

La ingesta guarda el calendario original local en `datasets/raw/holidays/original/`. El procesamiento genera `datasets/processed/silver/holidays_calendar.csv` y, si `pyarrow` esta disponible, tambien `holidays_calendar.parquet`.

## Open-Meteo

Open-Meteo es la fuente climatica principal del proyecto: no requiere API key y permite descargar el historico diario 2015-2024 por coordenadas representativas de cada provincia.

```env
OPEN_METEO_FROM_DATE=2015-10-01
OPEN_METEO_TO_DATE=2024-12-31
OPEN_METEO_LOCATIONS=
OPEN_METEO_TIMEZONE=Europe/Madrid
OPEN_METEO_MIN_SECONDS_BETWEEN_REQUESTS=5
OPEN_METEO_RETRY_ATTEMPTS=6
OPEN_METEO_RETRY_BASE_SECONDS=10
OPEN_METEO_SKIP_EXISTING=true
```

Si `OPEN_METEO_LOCATIONS` queda vacio, se descargan todas las capitales de provincia, Ceuta y Melilla. Para probar con pocas provincias:

```env
OPEN_METEO_LOCATIONS=madrid,barcelona,malaga
```

```bash
python scripts/run_pipeline.py --ingest --source open_meteo --dry-run
python scripts/run_pipeline.py --ingest --source open_meteo
```

La ingesta guarda los JSON originales locales en `datasets/raw/open_meteo/original/` y sus manifests en `datasets/raw/open_meteo/landing_manifest/`. En S3 conserva la capa `bronze/open_meteo/...`.
Si la API devuelve `429`, el conector espera y reintenta. Si una ejecucion se corta, vuelve a lanzar el mismo comando: con `OPEN_METEO_SKIP_EXISTING=true` reutiliza los ficheros ya descargados y continua con los que faltan.

## AENA

Los ficheros mensuales de AENA se descargan manualmente desde el portal de estadisticas de AENA y se guardan localmente en `datasets/raw/aena/`. El script no automatiza esa descarga; solo registra y procesa los Excel locales. Soporta los Excel historicos `.xls` y los `.xlsx` modernos:

```bash
python scripts/run_pipeline.py --ingest --source aena --dry-run
python scripts/run_pipeline.py --process --source aena --skip-s3-upload
```

El procesamiento genera:

- `datasets/processed/silver/aena_monthly_air_traffic.csv`
- `datasets/processed/silver/aena_monthly_air_traffic_by_province.csv`

La tabla gold incorpora las features `aena_passengers`, `aena_operations`, `aena_cargo_kg` y `aena_airport_count` por provincia y mes.

## Estructura

```text
config/                  Configuracion declarativa del proyecto
datasets/                Datos locales de apoyo, no versionar grandes datasets
docs/                    Arquitectura, decisiones y fuentes
notebooks/               Notebook principal y analisis incrementales del proyecto
scripts/run_pipeline.py  Script unico de despliegue, ingesta y procesamiento
```
