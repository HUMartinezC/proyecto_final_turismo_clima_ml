# Hito 1 - EDA y preparacion del dataset gold

## Enfoque del hito

El entregable principal del hito 1 se centra en la tabla gold
`tourism_weather_monthly_features`, que integra turismo, clima, calendario y
movilidad aerea con grano:

```text
province + year_month
```

La arquitectura de data lake por capas queda como soporte tecnico del proyecto,
pero el analisis exploratorio y la preparacion del conjunto de datos se realizan
sobre la tabla gold, que es la base directa para el modelado.

## Evidencia de ejecucion del pipeline

El pipeline se ejecuto reutilizando los datos ya ingeridos:

```bash
python scripts/run_pipeline.py --skip-ingest
```

Resultado relevante de la ejecucion:

- Validacion de identidad AWS con STS.
- Preparacion de bucket S3 y prefijos del data lake.
- Validacion/creacion de Glue database `tourism_weather_dev`.
- Validacion de Athena workgroup `primary`.
- Validacion de RDS MariaDB `tourism-weather-db`.
- Lambda omitida por falta de `LAMBDA_ROLE_ARN`, sin bloquear el hito.
- Tabla silver Open-Meteo: 5772 filas.
- Inventario Dataestur: 8 ficheros.
- Tabla silver Dataestur hotel occupancy: 5772 filas.
- Calendario de festivos: 774 filas.
- Tabla silver AENA aeropuerto-mes: 5769 filas.
- Tabla silver AENA provincia-mes: 4200 filas.
- Tabla gold final: 5772 filas.

La ejecucion finalizo correctamente en 29.3 segundos y genero:

```text
datasets/processed/gold/tourism_weather_monthly_features.csv
```

## Validacion de la tabla gold

La tabla gold contiene:

- 5772 filas.
- 31 columnas.
- 52 provincias.
- Rango temporal: octubre de 2015 a diciembre de 2024.
- 0 duplicados por `province + year_month`.
- 14 filas sin `hotel_overnights`, excluidas del dataset de entrenamiento.

El target principal es:

```text
hotel_overnights
```

La variable `hotel_occupancy_rate` queda documentada como target alternativo o
variable auxiliar para experimentos posteriores.

## EDA realizado

El notebook local `notebooks/proyecto_final_turismo_clima_local.ipynb` contiene:

- Inspeccion inicial de la tabla gold.
- Perfil de columnas: tipos, nulos, porcentaje de nulos y valores unicos.
- Estadisticas descriptivas: media, mediana, desviacion estandar, percentiles y
  moda.
- Analisis de valores faltantes.
- Comprobacion de duplicados por clave del grano.
- Deteccion de outliers mediante IQR.
- Visualizaciones de distribucion, dispersion, boxplots y correlaciones.
- Analisis de correlacion entre el target y variables explicativas.

## Preparacion del dataset

La preparacion se realiza sobre gold eliminando filas sin target. Para evitar
fuga temporal, el split se hace por meses completos:

- Train: 4562 filas.
- Test: 1196 filas.
- Proporcion aproximada: 79.2% / 20.8%.
- Sin solape de meses entre train y test.

## Transformaciones aplicadas

Se crean variables temporales:

- `year`
- `month`
- `quarter`
- `is_high_season`

Se crean transformaciones numericas:

- `hotel_overnights_log1p`
- `aena_passengers_log1p`
- `precipitation_sqrt`
- `temperature_2m_mean_sq`

Estas transformaciones ayudan a estabilizar distribuciones sesgadas y capturar
relaciones no lineales relevantes.

Tambien se crean discretizaciones interpretables:

- `temperature_bucket`
- `precipitation_bucket`
- `demand_segment`

## Dataset preparado para modelos

El preprocesado final aplica:

- Imputacion por mediana en variables numericas.
- Imputacion con `unknown` en variables categoricas.
- Escalado con `StandardScaler`.
- Encoding categorico con `OneHotEncoder`.

El dataset preparado queda con:

```text
X_train_prepared: 4562 x 99
X_test_prepared: 1196 x 99
```

El notebook muestra una vista de las primeras filas de `X_train_prepared` para
evidenciar que las features finales ya estan imputadas, escaladas y codificadas.

## Conclusion

El hito 1 queda cubierto: existe una tabla gold integrada, se ha realizado EDA
sobre ella y se ha preparado un conjunto modelable con transformaciones,
encoding, escalado y division train/test.
