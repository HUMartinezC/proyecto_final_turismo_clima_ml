# Hito 0 - Turismo, clima y demanda hotelera

## Problema de Machine Learning

Se plantea un problema supervisado de regresión: predecir la demanda turística mensual en España por provincia. Es supervisado porque se dispone de histórico de demanda hotelera y es regresión porque la variable a estimar es numérica.

La variable objetivo principal será `hotel_overnights`, es decir, pernoctaciones hoteleras mensuales por provincia. Como alternativa, si la cobertura de Dataestur resulta más estable en una agregación concreta, se podrá usar `hotel_occupancy_rate`. Ambas son variables continuas y permiten evaluar el modelo con MAE, RMSE y R2.

## Utilidad real

El sistema ayuda a anticipar ocupación hotelera, planificar recursos, detectar caídas o picos de demanda y entender cuánto explican el clima, los festivos y la movilidad en la llegada de turistas.

## Fuentes iniciales

La primera versión integrada del proyecto se apoya en fuentes con relación directa con la demanda turística:

- Dataestur: demanda turística, alojamientos, gasto y transporte. Es la fuente principal para el target.
- Open-Meteo: clima histórico diario, accesible sin API key y reproducible para todas las provincias.
- Festivos: calendario laboral generado localmente con el paquete `holidays`.
- AENA: pasajeros, operaciones y carga por aeropuerto. Los Excel mensuales se descargan manualmente y el script los procesa de forma automatizada.
- Movilidad terrestre: fuente candidata para explicar turismo nacional, viajes de proximidad y escapadas donde el aeropuerto no representa bien la entrada de visitantes.

AEMET queda como fuente oficial de contraste meteorológico opcional. No forma parte del flujo por defecto porque Open-Meteo cubre mejor la reproducibilidad inicial.

## Variables

Target candidato principal:

- `hotel_overnights`: pernoctaciones hoteleras mensuales por provincia.

Target alternativo:

- `hotel_occupancy_rate`: porcentaje de ocupación hotelera mensual.

Features principales:

- Turismo: viajeros, pernoctaciones históricas, estancia media, ocupación y gasto medio.
- Clima: temperatura media, máxima y mínima; precipitación acumulada; horas de lluvia; viento medio y máximo.
- Calendario: mes, temporada, número de festivos nacionales y regionales.
- Movilidad: pasajeros, operaciones y carga aeroportuaria agregados por provincia y mes; posible incorporación posterior de indicadores ferroviarios o terrestres.
- Geografía: provincia y comunidad autónoma.

## Grano de Integración

La tabla final `tourism_weather_monthly_features` tendrá como grano:

```text
provincia x mes
```

El campo temporal común será `year_month`. Las fuentes diarias, como Open-Meteo y festivos, se agregan a nivel mensual. Los datos de AENA ya tienen grano mensual por aeropuerto y se agregan a provincia. Si se incorpora movilidad terrestre, tendrá que normalizarse al mismo grano para que sea comparable.

## Tipo de Problema

- Aprendizaje supervisado.
- Regresión tabular con componente temporal mensual.
- Primer baseline: predicción mensual por provincia.

## Modelos previstos

- Random Forest Regressor: robusto ante relaciones no lineales y fácil de explicar con importancia de variables.
- XGBoost Regressor: buen rendimiento en datos tabulares con interacciones y estacionalidad.

Como baseline adicional puede usarse `Ridge` o `LinearRegression` para comparar contra modelos no lineales.

## Alcance del entregable inicial

Este entregable fija el problema, las fuentes y la arquitectura inicial. No pretende entrenar aún el modelo final, sino dejar una base defendible para las siguientes fases: ingesta, procesamiento, EDA, preparación de datos y entrenamiento.
