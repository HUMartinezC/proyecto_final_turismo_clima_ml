# Hito 0 - Turismo, clima y demanda hotelera

## Problema de Machine Learning

Se plantea un problema supervisado de regresión: predecir la demanda turística mensual en España por provincia. Es supervisado porque se dispone de histórico de demanda hotelera y es regresión porque la variable a estimar es numérica.

La variable objetivo principal sera `hotel_overnights`, es decir, pernoctaciones hoteleras mensuales por provincia. Como alternativa, si la cobertura de Dataestur resulta mas estable en una agregacion concreta, se podra usar `hotel_occupancy_rate`. Ambas son variables continuas y permiten evaluar el modelo con MAE, RMSE y R2.

## Utilidad real

El sistema ayuda a anticipar ocupacion hotelera, planificar recursos, detectar caidas o picos de demanda y entender cuanto explican el clima, los festivos y la movilidad en la llegada de turistas.

## Fuentes iniciales

La primera version integrada del proyecto se apoya en fuentes con relacion directa con la demanda turistica:

- Dataestur: demanda turistica, alojamientos, gasto y transporte. Es la fuente principal para el target.
- Open-Meteo: clima historico diario, accesible sin API key y reproducible para todas las provincias.
- Festivos: calendario laboral generado localmente con el paquete `holidays`.
- AENA: pasajeros, operaciones y carga por aeropuerto. Los Excel mensuales se descargan manualmente y el script los procesa de forma automatizada.
- Movilidad terrestre: fuente candidata para explicar turismo nacional, viajes de proximidad y escapadas donde el aeropuerto no representa bien la entrada de visitantes.

AEMET queda como fuente oficial de contraste meteorologico opcional. No forma parte del flujo por defecto porque Open-Meteo cubre mejor la reproducibilidad inicial.

## Variables

Target candidato principal:

- `hotel_overnights`: pernoctaciones hoteleras mensuales por provincia.

Target alternativo:

- `hotel_occupancy_rate`: porcentaje de ocupacion hotelera mensual.

Features principales:

- Turismo: viajeros, pernoctaciones historicas, estancia media, ocupacion y gasto medio.
- Clima: temperatura media, maxima y minima; precipitacion acumulada; horas de lluvia; viento medio y maximo.
- Calendario: mes, temporada, numero de festivos nacionales y regionales.
- Movilidad: pasajeros, operaciones y carga aeroportuaria agregados por provincia y mes; posible incorporacion posterior de indicadores ferroviarios o terrestres.
- Geografia: provincia y comunidad autonoma.

## Grano de Integracion

La tabla final `tourism_weather_monthly_features` tendra como grano:

```text
provincia x mes
```

El campo temporal comun sera `year_month`. Las fuentes diarias, como Open-Meteo y festivos, se agregan a nivel mensual. Los datos de AENA ya tienen grano mensual por aeropuerto y se agregan a provincia. Si se incorpora movilidad terrestre, tendra que normalizarse al mismo grano para que sea comparable.

## Tipo de Problema

- Aprendizaje supervisado.
- Regresion tabular con componente temporal mensual.
- Primer baseline: prediccion mensual por provincia.

## Modelos previstos

- Random Forest Regressor: robusto ante relaciones no lineales y facil de explicar con importancia de variables.
- XGBoost Regressor: buen rendimiento en datos tabulares con interacciones y estacionalidad.

Como baseline adicional puede usarse `Ridge` o `LinearRegression` para comparar contra modelos no lineales.

## Alcance del entregable inicial

Este entregable fija el problema, las fuentes y la arquitectura inicial. No pretende entrenar aun el modelo final, sino dejar una base defendible para las siguientes fases: ingesta, procesamiento, EDA, preparacion de datos y entrenamiento.
