# Tourism Weather ML

Proyecto de Machine Learning para estimar demanda hotelera mensual en España a partir de datos de turismo, clima, calendario y movilidad aeroportuaria.

## Objetivo

El problema se plantea como una regresion supervisada con `province + year_month`. La variable objetivo principal es `hotel_overnights`, procedente de Dataestur. El dataset final integra variables climaticas de Open-Meteo, festivos nacionales/autonomicos y movilidad aeroportuaria de AENA.

## Stack implementado

- AWS S3 como data lake por capas: `bronze`, `silver` y `gold`.
- AWS Glue Data Catalog para registrar las tablas externas.
- Amazon Athena para consultar los Parquet de S3 mediante SQL.
- Amazon RDS MariaDB como base relacional disponible para pruebas y resultados estructurados.
- AWS Lambda como recurso opcional si se configura un `LAMBDA_ROLE_ARN`.
- Python con `boto3`, `pandas`, `numpy`, `pyarrow`, `requests`, `holidays`, `matplotlib`, `seaborn`, `scikit-learn` y `xgboost`.

El procesamiento se ejecuta con Python y las tablas de Glue se crean o actualizan desde Athena mediante DDL.

## Fuentes de datos

| Fuente | Uso actual | Entrada |
|---|---|---|
| Dataestur | Demanda hotelera y variables turisticas | API REST |
| Open-Meteo | Historico meteorologico diario por provincia | API REST sin clave |
| Festivos | Calendario nacional y autonomico | Paquete `holidays` |
| AENA | Pasajeros, operaciones y carga por aeropuerto | Excel mensuales descargados manualmente |

AEMET queda fuera del flujo actual. Se conserva como fuente opcional de contraste oficial, pero `scripts/run_pipeline.py --source aemet` solo registra que no forma parte del pipeline implementado.

## Estructura

```text
config/                  Configuracion declarativa de fuentes
datasets/raw/            Originales locales y manifests de ingesta
datasets/processed/      Salidas locales reproducibles en silver y gold
docs/                    Documentacion tecnica del proyecto
enunciados/              Requisitos literales de las entregas
notebooks/               Notebooks local, cloud e indice
scripts/run_pipeline.py  Script unico de despliegue, ingesta, procesado y catalogo
```

La capa `bronze` existe en S3. En local, `datasets/raw/` cumple el mismo papel para evitar duplicar conceptos.

## Instalacion

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py --check-config
```

El fichero `.env` debe definir, como minimo, credenciales AWS validas, `S3_BUCKET_NAME`, `ATHENA_RESULTS_S3_URI` y la configuracion temporal de las fuentes.

## Ejecucion del pipeline

Flujo completo:

```bash
python scripts/run_pipeline.py
```

Simulacion sin descargas ni escrituras:

```bash
python scripts/run_pipeline.py --dry-run
```

Regenerar silver/gold usando datos ya descargados:

```bash
python scripts/run_pipeline.py --process --skip-s3-upload
```

Ejecutar despliegue y procesamiento sin volver a descargar fuentes:

```bash
python scripts/run_pipeline.py --skip-ingest
```

Crear o actualizar tablas externas en Glue Data Catalog sobre los Parquet de S3:

```bash
python scripts/run_pipeline.py --catalog
```

El flujo por defecto intenta despliegue idempotente, ingesta y procesamiento. Si se pasa `--deploy`, `--ingest`, `--process` o `--catalog`, solo se ejecutan las partes indicadas. `--source` limita la ingesta o el procesamiento a una fuente concreta.

## Salidas locales

El procesamiento genera, entre otras, estas tablas:

```text
datasets/processed/silver/open_meteo_monthly.csv
datasets/processed/silver/dataestur_hotel_occupancy_by_province.csv
datasets/processed/silver/holidays_calendar.csv
datasets/processed/silver/aena_monthly_air_traffic.csv
datasets/processed/silver/aena_monthly_air_traffic_by_province.csv
datasets/processed/gold/tourism_weather_monthly_features.csv
```

Si `pyarrow` esta disponible, tambien se generan versiones Parquet y se suben a S3 en rutas separadas por tabla y formato.

## Tablas en Athena

El catalogo crea tablas externas para las capas silver y gold:

```text
silver_open_meteo_monthly
silver_dataestur_hotel_occupancy_by_province
silver_holidays_calendar
silver_aena_monthly_air_traffic
silver_aena_monthly_air_traffic_by_province
gold_tourism_weather_monthly_features
```

Athena necesita una ubicacion de resultados configurada en el workgroup o en `ATHENA_RESULTS_S3_URI`.

## Notebooks

- `notebooks/proyecto_final_turismo_clima.ipynb`: indice del proyecto.
- `notebooks/proyecto_final_turismo_clima_cloud.ipynb`: notebook principal y fuente de verdad para resultados, leyendo gold desde S3 y validando Athena.
- `notebooks/proyecto_final_turismo_clima_local.ipynb`: ejecucion auxiliar para trabajar sin AWS; sus resultados exploratorios no sustituyen la seleccion final del notebook cloud.

Los notebooks cubren inspeccion inicial, estadisticas descriptivas, valores faltantes, duplicados, outliers, visualizaciones, correlaciones, preparacion del dataset, division temporal train/test y entrenamiento de modelos.

## Modelado

El target usado es `hotel_overnights`. Las filas sin target se excluyen del entrenamiento. La division se realiza por meses completos para evitar fuga temporal:

- Train: 4562 filas, de 2015-10 a 2023-01.
- Test: 1196 filas, de 2023-02 a 2024-12.

Modelos entrenados:

- Random Forest Regressor.
- Extra Trees Regressor.
- HistGradientBoosting Regressor.
- XGBoost Regressor.

Las metricas comparadas son MAE, RMSE y R2. El notebook cloud selecciona `ExtraTrees optimizado` mediante busqueda de hiperparametros:

- MAE: `47483.282`.
- RMSE: `118515.718`.
- R2: `0.990`.

`scripts/train_export_model.py` reproduce las features, discretizaciones e hiperparametros del modelo seleccionado en el notebook cloud.

El fine-tuning local especializado en provincias costeras e insulares se reproduce con:

```bash
python scripts/fine_tune_coastal_model.py
```

Esta variante reduce el RMSE un `8.19%` frente al modelo global evaluado sobre el mismo test costero. Los resultados y limitaciones se documentan en `docs/fine_tuning.md`.

Para comparar interactivamente ambos modelos mediante Gradio, solo en local:

```bash
python deployment/huggingface_space/app.py
```

## Representacion y despliegue

El mejor modelo puede exportarse como pipeline completo y generar figuras de evaluacion:

```bash
python scripts/train_export_model.py
```

Para desplegar el modelo y la demo Gradio en Hugging Face Hub:

```bash
python scripts/deploy_to_huggingface.py
```

El despliegue usa `HF_TOKEN`, `HF_MODEL_REPO_ID` y `HF_SPACE_REPO_ID`.

## Documentacion

- `docs/problema_ml.md`: problema, target, grano y variables.
- `docs/fuentes_datos.md`: fuentes usadas, fuentes descartadas y rango temporal.
- `docs/arquitectura.md`: arquitectura local/AWS y flujo de datos.
- `docs/decisiones_tecnicas.md`: decisiones, riesgos y mitigaciones.
- `docs/eda_preparacion.md`: EDA, limpieza, transformaciones y split.
- `docs/modelado.md`: modelos entrenados, metricas y seleccion.
- `docs/fine_tuning.md`: especializacion costera, comparacion y limitaciones.
- `docs/despliegue_hf.md`: exportacion del modelo y despliegue en Hugging Face.
