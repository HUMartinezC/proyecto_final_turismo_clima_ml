# Fuentes de datos definitivas

Para el MVP se priorizan pocas fuentes, de alta relacion con el target y faciles de justificar.

| Fuente | Uso | Motivo | Capa inicial |
|---|---|---|---|
| Dataestur | Demanda turistica, alojamientos, gasto y transporte | Fuente agregada y orientada a turismo; reduce complejidad frente a mezclar demasiadas APIs | S3 bronze + DocumentDB |
| AEMET OpenData | Clima observado e historico | Fuente oficial espanola para variables meteorologicas explicativas | S3 bronze + DocumentDB |
| Calendario laboral/festivos | Festivos, puentes y estacionalidad | Muy predictivo para turismo y facil de integrar por fecha/region | S3 bronze + RDS |
| AENA Open Data | Pasajeros por aeropuerto | Proxy de movilidad; util para mejorar el modelo si la cobertura territorial encaja | S3 bronze + RDS |

## Fuentes descartadas por ahora

- Copernicus ERA5: excelente pero demasiado pesado para el primer hito. Se puede incorporar si AEMET no cubre el historico necesario.
- OpenStreetMap: util para features geoespaciales, pero no imprescindible para predecir demanda mensual.
- Google Trends: interesante pero introduce dependencia externa y sesgos de busqueda.
- Redes sociales: alto coste de limpieza, ruido y restricciones de API.
- Eurostat/Banco de Espana/World Bank: utiles para contexto macro, pero menos directas para un primer modelo regional de demanda turistica.

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
- `rainy_days`
- `holiday_count`
- `bridge_days`
- `airport_passengers`
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

## Rango temporal inicial

Para entrenamiento se fija el rango 2015-10 a 2024-12, respetando la fecha minima disponible de Dataestur:

- 2015-10 a 2019: turismo moderno pre-COVID.
- 2020-2021: periodo anomalo que puede marcarse con una variable `covid_period`.
- 2022-2024: recuperacion y patron reciente.

Este rango equilibra volumen, relevancia y calidad esperable de las fuentes.
