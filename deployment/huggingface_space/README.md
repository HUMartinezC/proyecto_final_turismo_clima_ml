---
title: Tourism Weather ML
emoji: 🌦️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.14.0
python_version: 3.11
app_file: app.py
pinned: false
models:
  - HMartinezC/tourism-weather-model
---

# Tourism Weather ML

Aplicacion Gradio para estimar pernoctaciones hoteleras mensuales por provincia a partir de clima, calendario y movilidad aeroportuaria.

La interfaz usa selectores para provincia, mes, festivos y numero de aeropuertos; completa automaticamente el codigo regional y carga medianas historicas por provincia y mes para evitar combinaciones de entrada poco realistas.

Permite comparar el modelo global con una variante ajustada para las 24 provincias costeras e insulares y con `amazon/chronos-2`, un modelo de Hugging Face para forecasting de series temporales.

Chronos-2 recibe un formato compatible de serie temporal: `item_id` como provincia, `timestamp` como mes y `target` como pernoctaciones hoteleras. Esta referencia HF usa solo el historico mensual de la provincia, mientras que los modelos propios usan el formulario tabular con clima, calendario y movilidad.

El ejemplo inicial usa valores medianos aproximados del historico de Malaga en agosto. En modo comparacion, la prediccion principal conserva el modelo global como referencia y la variante costera se muestra como contraste.

Todas las provincias tienen presets historicos por mes generados desde la tabla gold. Al seleccionar una provincia o cambiar el mes, la interfaz actualiza clima, calendario y movilidad con valores coherentes con su historico.

Los codigos mostrados son codigos de comunidad autonoma usados por el calendario y el modelo, no codigos provinciales. La prediccion deriva internamente la comunidad desde la provincia seleccionada para evitar inconsistencias.

La tabla final conserva en memoria las cinco predicciones mas recientes de cada sesion. El historial no se comparte entre usuarios ni se guarda de forma permanente.
