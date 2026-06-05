# Fine-tuning del modelo costero e insular

## Objetivo

El proyecto usa un modelo tabular clasico, por lo que el equivalente practico al fine-tuning consiste en reentrenar y reajustar hiperparametros sobre un dataset mas especifico. Se ha creado un modelo especializado en provincias costeras e insulares, donde la demanda turistica presenta patrones estacionales y volumenes especialmente relevantes.

El segmento contiene 24 provincias o territorios:

```text
A Coruna, Alicante, Almeria, Asturias, Barcelona, Bizkaia, Cadiz, Cantabria,
Castellon, Ceuta, Gipuzkoa, Girona, Granada, Huelva, Illes Balears, Las Palmas,
Lugo, Malaga, Melilla, Murcia, Pontevedra, Santa Cruz de Tenerife, Tarragona,
Valencia
```

## Protocolo de comparacion

La comparacion evita fuga temporal y usa exactamente el mismo test para todos los modelos:

- Train global: 4562 filas, de 2015-10 a 2023-01.
- Train costero: 2108 filas, de 2015-10 a 2023-01.
- Test costero comun: 552 filas, de 2023-02 a 2024-12.
- Validacion interna para ajustar hiperparametros: bloque temporal de 2021-08 a 2023-01.
- Criterio de seleccion: menor RMSE de validacion.

Se comparan tres variantes:

1. `Global ExtraTrees`: modelo seleccionado en el notebook cloud, entrenado con todas las provincias.
2. `Coastal ExtraTrees`: mismo modelo y parametros, reentrenado solo con provincias costeras.
3. `Tuned coastal ExtraTrees`: modelo costero con busqueda de hiperparametros.

Este tercer modelo es el fine-tuning evaluado. El simple reentrenamiento costero se conserva como control para distinguir el efecto del dataset especifico del efecto del ajuste de parametros.

## Resultado

| Modelo | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Global ExtraTrees | 79878.541 | 170759.091 | 0.988463 |
| Coastal ExtraTrees | 85369.661 | 171529.063 | 0.988359 |
| Tuned coastal ExtraTrees | 78121.147 | 156769.870 | 0.990276 |

Frente al modelo global evaluado sobre el mismo test costero, el modelo ajustado:

- Reduce MAE un `2.20%`.
- Reduce RMSE un `8.19%`.
- Eleva R2 de `0.988463` a `0.990276`.

Los mejores parametros encontrados son:

```text
n_estimators=180
max_depth=None
min_samples_split=5
min_samples_leaf=1
max_features=0.7
bootstrap=False
random_state=42
```

## Interpretacion y limites

El modelo especializado reduce especialmente errores grandes, por lo que la mejora de RMSE es superior a la mejora de MAE. Sin embargo, no mejora de forma uniforme: reduce MAE en 13 de las 24 provincias. Destaca positivamente en Melilla, Las Palmas, Bizkaia, Malaga e Illes Balears, mientras que empeora de forma clara en Ceuta y Santa Cruz de Tenerife.

Por ello, el modelo costero ajustado es util como variante especializada y demuestra una mejora agregada, pero no debe sustituir automaticamente al modelo global para todas las provincias costeras. Antes de desplegarlo conviene aplicar una regla de seleccion por provincia o ampliar la validacion con varios cortes temporales.

## Reproduccion local

```bash
python scripts/fine_tune_coastal_model.py
```

El script genera:

- Modelo local: `models/tourism_weather_coastal_extra_trees.joblib`.
- Metadatos y predicciones: `models/coastal_model_metadata.json` y `models/coastal_test_predictions.csv`.
- Comparaciones reproducibles: `reports/fine_tuning/`.
- Figuras: `reports/figures/coastal_model_metrics.png` y `reports/figures/coastal_monthly_predictions.png`.

No se publica ni modifica ningun recurso de Hugging Face.

## Aplicacion Gradio local

La comparacion interactiva entre el modelo global y el modelo costero ajustado se inicia con:

```bash
python deployment/huggingface_space/app.py
```

La aplicacion identifica si la provincia pertenece al segmento, muestra las dos predicciones cuando procede y conserva las ultimas cinco comparaciones en memoria. Se usa el mismo script que posteriormente se publica en la Space, pero esta ejecucion es exclusivamente local.

El ejemplo inicial representa valores medianos aproximados de Malaga en agosto. En modo comparacion, el modelo global permanece como referencia y se avisa cuando la diferencia entre modelos supera el 20%, ya que una divergencia elevada puede indicar una combinacion de entrada poco representativa.

Para facilitar la demostracion, las diez provincias con mayor volumen acumulado de pernoctaciones disponen de presets embebidos en la aplicacion. Cada preset usa las medianas historicas del mes con mayor demanda media de la provincia, por lo que funciona tambien en la Space sin acceder al dataset gold.
