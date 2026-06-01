# Problema de Machine Learning

## Planteamiento

El proyecto resuelve un problema supervisado de regresion: estimar la demanda hotelera mensual en España por provincia.

La variable objetivo principal es:

```text
hotel_overnights
```

Esta variable representa pernoctaciones hoteleras mensuales por provincia y procede de Dataestur. Como variable auxiliar se conserva `hotel_occupancy_rate`, que permite analizar ocupacion relativa, pero no se usa como target principal en el flujo actual.

## Utilidad

El modelo permite anticipar demanda turistica, detectar picos o caidas por territorio y analizar cuanto aportan clima, calendario y movilidad a la explicacion de la demanda hotelera.

## Grano de integracion

La tabla final `tourism_weather_monthly_features` usa el grano:

```text
province + year_month
```

Las fuentes diarias se agregan a mes y provincia. AENA parte de datos mensuales por aeropuerto y se agrega a provincia mediante una correspondencia aeropuerto-provincia.

## Variables principales

- Turismo: pernoctaciones, viajeros, estancia media y ocupacion hotelera.
- Clima: temperatura media, maxima y minima; precipitacion; lluvia; viento.
- Calendario: mes, trimestre, temporada alta y numero de festivos.
- Movilidad: pasajeros, operaciones, carga y numero de aeropuertos por provincia.
- Territorio: provincia y comunidad autonoma.

## Modelos usados

El entrenamiento actual compara varios modelos de regresion tabular:

- Random Forest Regressor.
- Extra Trees Regressor.
- HistGradientBoosting Regressor.
- XGBoost Regressor.

La seleccion del modelo se basa en MAE, RMSE y R2 sobre un conjunto de test temporal.
