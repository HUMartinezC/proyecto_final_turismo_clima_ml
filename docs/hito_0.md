# Hito 0 - Turismo, clima y demanda hotelera

## Problema de Machine Learning

Se plantea un problema supervisado de regresion: predecir la demanda turistica mensual en Espana por provincia o comunidad autonoma.

La variable objetivo inicial sera `hotel_overnights` o, si la fuente final lo permite con mejor cobertura, `hotel_occupancy_rate`. Ambas son variables continuas y permiten evaluar el modelo con MAE, RMSE y R2.

## Utilidad real

El sistema ayuda a anticipar ocupacion hotelera, planificar recursos, detectar caidas o picos de demanda y entender cuanto explican el clima, los festivos y la movilidad en la llegada de turistas.

## Variables

Target candidato principal:

- `hotel_overnights`: pernoctaciones hoteleras mensuales por region.

Target alternativo:

- `hotel_occupancy_rate`: porcentaje de ocupacion hotelera mensual.

Features principales:

- Turismo: viajeros, pernoctaciones historicas, estancia media, ocupacion, gasto medio.
- Clima: temperatura media, maxima y minima; precipitacion acumulada; dias de lluvia; viento medio; eventos extremos.
- Calendario: mes, trimestre, semana, temporada alta/baja, numero de festivos, puentes.
- Movilidad: pasajeros aeroportuarios por aeropuerto cercano o region.
- Geografia: provincia/CCAA, zona turistica y distancia aproximada a aeropuerto si se incorpora AENA.

## Tipo de problema

- Aprendizaje supervisado.
- Regresion tabular y temporal.
- Primer baseline: prediccion mensual por region.

## Modelos previstos

- Random Forest Regressor: robusto ante relaciones no lineales y facil de explicar con importancia de variables.
- XGBoost Regressor: buen rendimiento en datos tabulares con interacciones y estacionalidad.

Como baseline adicional puede usarse `Ridge` o `LinearRegression` para comparar contra modelos no lineales.
