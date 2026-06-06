# Despliegue en Hugging Face

## Objetivo

El modelo seleccionado se exporta como pipeline completo de scikit-learn y se publica en Hugging Face Hub. La demo se despliega como una Space de Gradio que permite introducir variables de clima, calendario y movilidad para obtener una prediccion en tiempo real.

## Entrenamiento y exportacion

```bash
python scripts/train_export_model.py
```

El script genera:

```text
models/tourism_weather_extra_trees.joblib
models/model_metadata.json
models/sample_input.json
models/test_predictions.csv
models/chronos_context.csv
models/province_month_presets.csv
models/feature_importance.csv
reports/figures/predictions_vs_actual.png
reports/figures/residuals.png
reports/figures/monthly_actual_vs_predicted.png
reports/figures/feature_importance.png
```

Las figuras representan datos reales frente a predicciones, residuos, evolucion mensual agregada e importancia de variables.

## Variables de entorno

```env
HF_TOKEN=
HF_MODEL_REPO_ID=usuario/tourism-weather-model
HF_SPACE_REPO_ID=usuario/tourism-weather-demo
```

`HF_TOKEN` debe tener permisos para crear y escribir en repositorios de Hugging Face.
`HF_MODEL_REPO_ID` y `HF_SPACE_REPO_ID` son opcionales para el script Python: si faltan, se generan como `<usuario>/tourism-weather-model` y `<usuario>/tourism-weather-demo`.

## Despliegue recomendado con HF CLI

```bash
hf auth login
python scripts/train_export_model.py
```

Crear o reutilizar el repositorio del modelo:

```bash
hf repos create "$HF_MODEL_REPO_ID" --type model --exist-ok
hf upload "$HF_MODEL_REPO_ID" models . --type model --commit-message "Upload tourism weather model"
```

Crear o reutilizar la Space Gradio:

```bash
hf repos create "$HF_SPACE_REPO_ID" --type space --space-sdk gradio --exist-ok
hf upload "$HF_SPACE_REPO_ID" deployment/huggingface_space . --type space --commit-message "Upload Gradio app"
```

Configurar el repositorio del modelo como secreto de la Space:

```bash
hf spaces secrets add "$HF_SPACE_REPO_ID" -s HF_MODEL_REPO_ID="$HF_MODEL_REPO_ID"
```

Si el repositorio del modelo es privado, la Space tambien necesita un token con permiso de lectura:

```bash
hf spaces secrets add "$HF_SPACE_REPO_ID" -s HF_TOKEN="$HF_TOKEN"
```

Comprobar el estado y los logs:

```bash
hf spaces info "$HF_SPACE_REPO_ID"
hf spaces logs "$HF_SPACE_REPO_ID"
```

Este flujo es el mas claro para gestionar Spaces desde agentes o terminal, porque separa autenticacion, creacion de repositorios, subida de artefactos y gestion de secretos.

## Despliegue automatizado con Python

Como alternativa, el repo incluye un script que automatiza los mismos pasos con `huggingface_hub`:

```bash
python scripts/deploy_to_huggingface.py
```

El script crea o reutiliza:

- Un repositorio de modelo para los artefactos.
- Una Space Gradio para la aplicacion.

Tambien configura `HF_MODEL_REPO_ID` como variable de la Space para que la app descargue el modelo desde el repositorio correspondiente.
Si se usa `--private`, tambien configura `HF_TOKEN` como secreto de la Space para que pueda leer el repositorio privado del modelo.

## Estado del despliegue

El despliegue esta operativo:

- Modelo: `https://huggingface.co/HMartinezC/tourism-weather-model`
- Space: `https://huggingface.co/spaces/HMartinezC/tourism-weather-demo`

El script elimina de la Space cualquier artefacto de modelo antiguo, publica el modelo en un repositorio separado, configura `HF_MODEL_REPO_ID`, reinicia la Space y espera hasta confirmar que el runtime esta operativo.

Esta separacion evita que archivos grandes gestionados por LFS formen parte del checkout de build de la Space. La version anterior contenia el modelo dentro de la Space y fallaba durante el build con `exit code 128`, antes de arrancar la aplicacion Python.

## Comparacion con Hugging Face

La Space integra `amazon/chronos-2` como modelo externo de Hugging Face para forecasting de series temporales. Para mantener la comparacion simple y reproducible, Chronos-2 recibe un contexto compatible generado en `models/chronos_context.csv`:

```text
item_id    -> province
timestamp  -> year_month
target     -> hotel_overnights
```

El modelo propio y la variante costera siguen usando el formulario tabular con clima, calendario y movilidad aeroportuaria. Chronos-2 actua como referencia zero-shot basada exclusivamente en el historico mensual de pernoctaciones de la provincia seleccionada.

La comparacion no fuerza a Chronos-2 a usar exactamente las mismas variables explicativas que el pipeline ExtraTrees; compara los tres modelos sobre el mismo target y deja visible la diferencia metodologica entre regresion tabular supervisada y forecasting temporal.

Para evitar comparaciones artificiales, la Space carga `models/province_month_presets.csv`, una tabla de medianas historicas por provincia y mes. Asi, al cambiar de provincia o de mes, los campos de clima, calendario y movilidad se actualizan con valores plausibles para ese territorio.

## Fine-tuning integrado localmente

Se ha entrenado y evaluado localmente una variante especializada en las 24 provincias costeras e insulares. El modelo ajustado reduce el RMSE un `8.19%` y el MAE un `2.20%` frente al modelo global sobre el mismo test costero.

La variante esta integrada y publicada mediante `deployment/huggingface_space/app.py`; el mismo script tambien permite probarla localmente. El protocolo, los resultados y sus limitaciones se documentan en `docs/fine_tuning.md`.
