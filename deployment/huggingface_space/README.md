---
title: Tourism Weather ML
emoji: 🌦️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
---

# Tourism Weather ML

Aplicacion Gradio para estimar pernoctaciones hoteleras mensuales por provincia a partir de clima, calendario y movilidad aeroportuaria.

La interfaz usa selectores para provincia, mes, festivos y numero de aeropuertos; completa automaticamente el codigo regional y limita las variables numericas a rangos observados razonables.

Los codigos mostrados son codigos de comunidad autonoma usados por el calendario y el modelo, no codigos provinciales. La prediccion deriva internamente la comunidad desde la provincia seleccionada para evitar inconsistencias.

La tabla final conserva en memoria las cinco predicciones mas recientes de cada sesion. El historial no se comparte entre usuarios ni se guarda de forma permanente.
