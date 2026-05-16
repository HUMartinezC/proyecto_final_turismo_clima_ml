# Fuentes de datos definitivas

Para la primera version integrada se priorizan fuentes de alta relacion con el target y faciles de justificar. La idea es construir una base solida antes de ampliar con fuentes menos directas.

| Fuente | Uso | Motivo | Capa inicial |
|---|---|---|---|
| Dataestur | Demanda turística, alojamientos, gasto y transporte | Fuente agregada y orientada a turismo; reduce complejidad frente a mezclar demasiadas APIs | S3 bronze + DocumentDB |
| Open-Meteo Historical Weather | Clima histórico diario por provincia | Fuente climática principal por cobertura, reproducibilidad y ausencia de API key | S3 bronze |
| Calendario laboral/festivos | Festivos, puentes y estacionalidad | Muy predictivo para turismo y fácil de integrar por fecha/región | S3 bronze + RDS |
| AENA Open Data | Pasajeros, operaciones y carga por aeropuerto | Proxy de movilidad; útil para mejorar el modelo si la cobertura territorial encaja. Descarga manual de Excel mensuales y procesamiento automatizado desde `datasets/raw/aena/` | S3 bronze + RDS |
| Movilidad terrestre | Viajes nacionales, desplazamientos de proximidad, posible conectividad ferroviaria/carretera | Fuente candidata para complementar AENA y explicar mejor turismo nacional o local | S3 bronze + RDS |
| AEMET OpenData | Clima observado oficial | Fuente oficial española de contraste, opcional y fuera del flujo por defecto | S3 bronze + DocumentDB |

## Fuentes descartadas por ahora

- Copernicus ERA5: excelente pero demasiado pesado para la primera integracion. Se puede incorporar si Open-Meteo no cubre alguna variable necesaria.
- OpenStreetMap: util para features geoespaciales, pero no imprescindible para predecir demanda mensual.
- Google Trends: interesante pero introduce dependencia externa y sesgos de busqueda.
- Redes sociales: alto coste de limpieza, ruido y restricciones de API.
- Eurostat/Banco de España/World Bank: utiles para contexto macro, pero menos directas para un primer modelo regional de demanda turistica.

## Grano de integracion

La tabla final `tourism_weather_monthly_features` tendra, como minimo:

- `year_month`
- `region_id`
- `region_name`
- `hotel_overnights`
- `hotel_occupancy_rate`
- `avg_temperature`
- `max_temperature`
- `min_temperature`
- `precipitation_mm`
- `rain_hours`
- `holiday_count`
- `airport_passengers`
- `airport_operations`
- `airport_cargo_kg`
- `land_mobility_index` o variables terrestres equivalentes si la fuente elegida lo permite
- `season`

## Uso de la API de Dataestur

Dataestur dispone de API publica en `https://www.dataestur.es/apidata/`. La propia interfaz permite seleccionar una consulta, probarla y copiar una `Request URL` reutilizable desde Python, curl o herramientas de BI. Su OpenAPI publica como servidor `https://dataestur.azure-api.net/API-SEGITTUR-v1/`.

Para el proyecto se recomienda empezar por estos endpoints:

| Endpoint | Uso |
|---|---|
| `EOH_PROV_DL` | Target principal por provincia: ocupacion, viajeros y pernoctaciones hoteleras |
| `EOH_CCAA_DL` | Target alternativo/agregado por CCAA |
| `FRONTUR_DL` | Llegadas de turistas internacionales |
| `ETR_DL` | Turismo de residentes |
| `EGATUR_DL` | Gasto turistico internacional |
| `AENA_DESTINOS_DL` | Trafico aereo como proxy de movilidad |
| `VALORES_CLIMATOLOGICOS_TEMPERATURA_DL` | Temperatura climatologica |
| `VALORES_CLIMATOLOGICOS_PRECIPITACION_DL` | Precipitacion climatologica |
| `IND_RENTABILIDAD_PROVINCIA_DL` | Rentabilidad hotelera por provincia |

El conector del repo puede descargar estos endpoints desde `.env`:

```text
DATAESTUR_ENDPOINTS=EOH_PROV_DL,EOH_CCAA_DL,FRONTUR_DL
```

Tambien puede leer una URL generada desde la interfaz de Dataestur:

```text
DATAESTUR_EOH_REQUEST_URL=https://www.dataestur.es/...
```

Buenas practicas: limitar peticiones, usar filtros concretos y respetar una frecuencia aproximada de 10 solicitudes por minuto.

## Uso de Open-Meteo

Open-Meteo es la fuente climatica principal. Permite descargar historico diario por coordenadas sin API key, lo que facilita reproducibilidad para todas las provincias.

Variables climaticas usadas inicialmente:

- `temperature_2m_mean`
- `temperature_2m_max`
- `temperature_2m_min`
- `precipitation_sum`
- `rain_sum`
- `precipitation_hours`
- `wind_speed_10m_mean`
- `wind_speed_10m_max`

Los JSON originales se guardan en `datasets/raw/open_meteo/original/` y se procesan a tabla mensual en `datasets/processed/silver/open_meteo_monthly.csv`.

## Uso de AENA Open Data

Los ficheros de AENA se descargan manualmente desde el portal de estadisticas de AENA, mes a mes. El script no automatiza esta descarga porque AENA publica los informes como Excel descargables y el formato/nombre de hoja cambia entre años.

Convencion local:

```text
datasets/raw/aena/01.Enero-Definitivo-2015.xls
datasets/raw/aena/01_Enero_Definitivo_2024.xlsx
```

El nombre debe conservar el número de mes y el año para que el procesamiento pueda inferir `year_month`. El script `scripts/run_pipeline.py` procesa los Excel locales con:

```bash
python scripts/run_pipeline.py --process --source aena --skip-s3-upload
```

La salida normalizada queda en:

```text
datasets/processed/silver/aena_monthly_air_traffic.csv
datasets/processed/silver/aena_monthly_air_traffic_by_province.csv
```

## Movilidad terrestre

La movilidad terrestre se considera una ampliacion natural del bloque de movilidad. AENA explica bien parte del turismo internacional y de destinos con aeropuerto relevante, pero puede quedarse corta para viajes nacionales, escapadas de fin de semana o provincias donde la llegada principal se produce por tren o carretera.

La fuente candidata mas interesante es el estudio de movilidad del Ministerio de Transportes basado en datos anonimizados de movilidad, siempre que permita descargar informacion con granularidad temporal y territorial compatible con el proyecto. Como alternativa mas sencilla, algunas tablas del INE pueden servir como indices mensuales generales de transporte de viajeros, aunque con menor detalle territorial.

Esta fuente no debe incorporarse solo por aumentar el numero de datasets. Se incorporara si aporta una variable mensual defendible y comparable con el grano `provincia x mes`.

## Rango temporal inicial

Para entrenamiento se fija el rango 2015-10 a 2024-12, respetando la fecha minima disponible de Dataestur:

- 2015-10 a 2019: turismo moderno pre-COVID.
- 2020-2021: periodo anomalo que puede marcarse con una variable `covid_period`.
- 2022-2024: recuperacion y patron reciente.

Este rango equilibra volumen, relevancia y calidad esperable de las fuentes.
