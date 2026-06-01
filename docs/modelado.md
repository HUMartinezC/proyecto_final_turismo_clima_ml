# Modelado y validacion

## Dataset de entrenamiento

El entrenamiento usa la tabla gold preparada desde `tourism_weather_monthly_features`. El target es:

```text
hotel_overnights
```

Las 14 filas sin target se excluyen. El split se hace por meses completos para evitar fuga temporal:

- Train: 4562 filas.
- Test: 1196 filas.

Tras imputacion, transformaciones, escalado y encoding, el conjunto preparado queda con 99 features.

## Modelos comparados

Se entrenan modelos ensemble y boosting adecuados para regresion tabular:

| Modelo | Configuracion |
|---|---|
| Random Forest | Profundidad libre y profundidad 8 |
| Extra Trees | Profundidad libre y profundidad 10 |
| HistGradientBoosting | Configuracion shallow y deep |
| XGBoost | Configuracion shallow y profundidad 5 |

## Metricas

La comparacion usa:

- MAE.
- RMSE.
- R2.

## Resultados actuales

| Modelo | RMSE | MAE | R2 |
|---|---:|---:|---:|
| ExtraTrees depth=10 | 119598.386 | 58741.780 | 0.990 |
| ExtraTrees depth=None | 121145.363 | 47611.640 | 0.990 |
| XGBoost depth=5 | 161776.414 | 65685.238 | 0.982 |
| XGBoost shallow | 176416.970 | 84567.447 | 0.978 |
| HistGradientBoosting shallow | 176941.497 | 70580.243 | 0.978 |
| RandomForest depth=None | 177393.055 | 63820.768 | 0.978 |
| HistGradientBoosting deep | 177789.146 | 71544.613 | 0.978 |
| RandomForest depth=8 | 181992.707 | 78162.984 | 0.977 |

## Seleccion

El modelo seleccionado es `ExtraTreesRegressor` con profundidad maxima 10, porque obtiene el menor RMSE en test y mantiene R2 alto. El RMSE se usa como criterio principal porque penaliza con mas fuerza los errores grandes, relevantes en provincias o meses con volumen turistico elevado.
