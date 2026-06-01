# Fuentes de datos

## Fuentes integradas

| Fuente | Uso | Grano original | Papel en el dataset |
|---|---|---|---|
| Dataestur | Demanda hotelera | Provincia/comunidad y mes | Target y variables turisticas |
| Open-Meteo Historical Weather | Clima diario | Coordenada y dia | Variables climaticas agregadas a provincia-mes |
| `holidays` | Festivos nacionales y autonomicos | Region y dia | Estacionalidad y calendario |
| AENA Open Data | Trafico aeroportuario | Aeropuerto y mes | Proxy de movilidad agregado a provincia-mes |

## Fuentes no integradas

- AEMET OpenData: fuente oficial de contraste meteorologico. No forma parte del pipeline actual.
- Movilidad terrestre: candidata para mejorar turismo nacional y de proximidad si se encuentra una fuente mensual y territorialmente compatible.
- Copernicus ERA5: potente, pero innecesaria frente a Open-Meteo para el alcance actual.
- OpenStreetMap: util para features geoespaciales, pero no imprescindible para el modelo tabular mensual.
- Google Trends y redes sociales: aportan ruido, sesgos y dependencias externas menos controlables.

## Tabla gold

La tabla final es:

```text
tourism_weather_monthly_features
```

Grano:

```text
province + year_month
```

Columnas principales actuales:

- `province`
- `region_code`
- `year_month`
- `year`
- `month`
- `hotel_overnights`
- `hotel_travelers`
- `hotel_stay_avg`
- `hotel_occupancy_rate`
- `temperature_2m_mean_avg`
- `temperature_2m_max_avg`
- `temperature_2m_min_avg`
- `precipitation_sum_total`
- `rain_sum_total`
- `precipitation_hours_total`
- `wind_speed_10m_mean_avg`
- `wind_speed_10m_max_avg`
- `national_holiday_count`
- `regional_holiday_count`
- `total_holiday_count`
- `aena_passengers`
- `aena_operations`
- `aena_cargo_kg`
- `aena_airport_count`

## Dataestur

Dataestur publica una API en `https://www.dataestur.es/apidata/`. El proyecto usa una seleccion curada de endpoints relacionados con demanda hotelera y contexto turistico.

Endpoint principal:

```text
EOH_PROV_DL
```

Este endpoint aporta el target `hotel_overnights` por provincia y mes.

## Open-Meteo

Open-Meteo es la fuente climatica principal. Permite descargar historico diario por coordenadas sin API key. Las capitales de provincia se usan como coordenadas representativas.

Variables base:

- `temperature_2m_mean`
- `temperature_2m_max`
- `temperature_2m_min`
- `precipitation_sum`
- `rain_sum`
- `precipitation_hours`
- `wind_speed_10m_mean`
- `wind_speed_10m_max`

El procesamiento agrega estas variables a nivel mensual.

## Festivos

El calendario se genera con el paquete `holidays`, cubriendo festivos nacionales y autonomicos. Las fechas se agregan por provincia y mes para obtener contadores de festivos.

## AENA

Los ficheros de AENA se descargan manualmente desde el portal de estadisticas. El script procesa Excel `.xls` y `.xlsx` colocados en:

```text
datasets/raw/aena/
```

Las tablas silver generadas son:

```text
datasets/processed/silver/aena_monthly_air_traffic.csv
datasets/processed/silver/aena_monthly_air_traffic_by_province.csv
```

## Rango temporal

El rango integrado es de 2015-10 a 2024-12. Esta ventana respeta la disponibilidad del target y conserva periodos pre-COVID, COVID y recuperacion posterior.
