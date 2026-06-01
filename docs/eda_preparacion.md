# EDA y preparacion de datos

## Dataset analizado

El analisis exploratorio y la preparacion se realizan sobre la tabla gold:

```text
tourism_weather_monthly_features
```

Cada fila representa una provincia y un mes. La tabla integra turismo, clima, calendario y movilidad aeroportuaria.

## Validacion de la tabla gold

La tabla gold actual contiene:

- 5772 filas.
- 31 columnas.
- 52 provincias.
- Rango temporal de 2015-10 a 2024-12.
- 0 duplicados por `province + year_month`.
- 14 filas sin `hotel_overnights`, excluidas del entrenamiento.

## EDA realizado

Los notebooks local y cloud incluyen:

- Inspeccion inicial de registros.
- Analisis de columnas, tipos, nulos y valores unicos.
- Estadisticas descriptivas: media, mediana, moda, desviacion estandar y percentiles.
- Analisis de valores faltantes.
- Comprobacion de duplicados por clave del grano.
- Deteccion de outliers mediante IQR.
- Histogramas, diagramas de dispersion, boxplots y mapa de correlaciones.
- Correlaciones entre el target y las variables explicativas.

## Criterios de limpieza

- Las filas sin `hotel_overnights` se excluyen porque el target falta en origen.
- Los outliers no se eliminan automaticamente: en turismo pueden representar demanda real de provincias grandes, temporadas altas o destinos vacacionales.
- Las variables irrelevantes o con riesgo de fuga se excluyen del set de features de modelado.
- Las variables altamente relacionadas con el target, como `viajeros_hotel`, se reservan para analisis y no se incorporan como predictor directo del target principal.

## Transformaciones

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

Tambien se generan discretizaciones interpretables:

- `temperature_bucket`
- `precipitation_bucket`
- `demand_segment`

## Preparacion para modelos

El preprocesado aplica:

- Imputacion por mediana en variables numericas.
- Imputacion con `unknown` en variables categoricas.
- Escalado con `StandardScaler`.
- Encoding categorico con `OneHotEncoder`.

La division train/test se realiza por meses completos:

- Train: 4562 filas, de 2015-10 a 2023-01.
- Test: 1196 filas, de 2023-02 a 2024-12.

No hay solape temporal entre entrenamiento y prueba.
