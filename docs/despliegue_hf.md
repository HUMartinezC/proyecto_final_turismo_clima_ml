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

Tambien configura `HF_MODEL_REPO_ID` como secreto de la Space para que la app descargue el modelo desde el repositorio correspondiente.
Si se usa `--private`, tambien configura `HF_TOKEN` como secreto de la Space para que pueda leer el repositorio privado del modelo.

## Estado del despliegue

El token de Hugging Face esta configurado en el entorno local. Para completar el despliegue tambien deben definirse `HF_MODEL_REPO_ID` y `HF_SPACE_REPO_ID`, ejecutar el script y conservar las URLs resultantes como evidencia.

## Comparacion con Hugging Face

El modelo propio es un pipeline tabular supervisado entrenado con datos integrados del proyecto. Los modelos disponibles en Hugging Face suelen estar orientados a texto, imagen o series genericas; no contienen de forma nativa las variables especificas de turismo, clima, festivos y movilidad por provincia. Por eso la comparacion se plantea a nivel funcional: el modelo propio esta especializado en el dataset del proyecto y la Space demuestra inferencia interactiva sobre el mismo esquema de features.

## Fine-tuning pendiente

En modelos tabulares clasicos, el equivalente practico al fine-tuning es reentrenar o reajustar hiperparametros con un subconjunto mas especifico. Esta parte aun no esta ejecutada. Una mejora razonable seria especializar el modelo por comunidad autonoma, litoral/interior o temporada alta, y comparar las metricas frente al modelo global.
