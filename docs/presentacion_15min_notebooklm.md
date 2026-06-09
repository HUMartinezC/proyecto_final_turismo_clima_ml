# Tourism Weather ML - Fuente para generar una presentacion de 15 minutos

Este documento resume el proyecto para generar una presentacion de defensa academica de unos 15 minutos. La presentacion debe tener entre 10 y 12 diapositivas, en español.

## 1. Resumen del proyecto

Tourism Weather ML es un proyecto de Machine Learning para estimar la demanda hotelera mensual en Espana por provincia. El problema se formula como regresion supervisada.

- Target: `hotel_overnights`.
- Unidad de analisis: `province + year_month`.
- Tabla final: `tourism_weather_monthly_features`.
- Rango temporal: 2015-10 a 2024-12.
- Ambito: 52 provincias espanolas.

La idea principal es combinar datos de turismo, clima, calendario y movilidad aeroportuaria para anticipar pernoctaciones hoteleras mensuales.

## 2. Utilidad del proyecto

El modelo permite:

- Anticipar picos y caidas de demanda hotelera.
- Analizar patrones por provincia y mes.
- Medir el valor de variables externas como clima, festivos y movilidad.
- Construir una solucion reproducible desde ingesta de datos hasta despliegue.

## 3. Fuentes de datos

Fuentes integradas:

| Fuente | Papel | Grano original |
|---|---|---|
| Dataestur | Target y variables turisticas | Provincia/comunidad y mes |
| Open-Meteo | Clima historico diario | Coordenada y dia |
| holidays | Festivos nacionales y autonomicos | Region y dia |
| AENA | Movilidad aeroportuaria | Aeropuerto y mes |

Dataestur aporta el target principal `hotel_overnights`. Open-Meteo aporta temperatura, precipitacion, lluvia y viento. El paquete `holidays` genera los festivos nacionales y autonomicos. AENA aporta pasajeros, operaciones, carga y numero de aeropuertos por provincia.

Fuentes no integradas:

- Movilidad terrestre, por falta de fuente mensual y territorial compatible.
- Copernicus ERA5, descartada porque Open-Meteo cubria el alcance.
- OpenStreetMap, util pero no imprescindible.
- Google Trends y redes sociales, por ruido y dependencias externas.

## 4. Arquitectura de datos

El proyecto combina ejecucion local reproducible con arquitectura cloud en AWS.

Componentes:

- Python para ingesta, transformacion y automatizacion.
- Amazon S3 como data lake.
- Capas `bronze`, `silver` y `gold`.
- AWS Glue Data Catalog para registrar tablas externas.
- Amazon Athena para consultar Parquet en S3.
- Amazon RDS MariaDB preparado para pruebas o resultados estructurados.
- AWS Lambda preparado como automatizacion opcional.
- Hugging Face Hub y Spaces para publicar el modelo y la demo.

Flujo general:

```text
Fuentes externas
-> raw / S3 bronze
-> silver normalizado por fuente
-> gold integrado por provincia y mes
-> EDA y entrenamiento
-> modelo exportado
-> Hugging Face Hub + Gradio Space
```

Script principal:

```bash
python scripts/run_pipeline.py
```

## 5. Dataset final

La tabla gold `tourism_weather_monthly_features` integra turismo, clima, calendario y movilidad.

Resumen:

- 5772 filas.
- 31 columnas.
- 52 provincias.
- Rango temporal de 2015-10 a 2024-12.
- 0 duplicados por `province + year_month`.
- 14 filas sin `hotel_overnights`, excluidas del entrenamiento.

Variables principales:

- Turismo: pernoctaciones, viajeros, estancia media y ocupacion hotelera.
- Clima: temperatura media, maxima y minima; precipitacion; lluvia; viento.
- Calendario: mes, trimestre, temporada alta y festivos.
- Movilidad: pasajeros, operaciones, carga y aeropuertos AENA.
- Territorio: provincia y comunidad autonoma.

## 6. EDA y preparacion

Analisis realizado:

- Revision de columnas, tipos, nulos y valores unicos.
- Estadisticas descriptivas.
- Comprobacion de duplicados.
- Deteccion de outliers mediante IQR.
- Histogramas, dispersiones, boxplots y correlaciones.

Decisiones importantes:

- Las filas sin target se eliminan solo para entrenamiento.
- Los outliers no se eliminan automaticamente porque pueden representar demanda turistica real.
- Variables con riesgo de fuga, como `hotel_travelers`, se reservan para analisis y no se usan como predictor directo.
- El split se realiza por meses completos para evitar fuga temporal.

Transformaciones:

- Variables temporales: `year`, `month`, `quarter`, `is_high_season`.
- Transformaciones numericas: `hotel_overnights_log1p`, `aena_passengers_log1p`, `precipitation_sqrt`, `temperature_2m_mean_sq`.
- Discretizaciones: segmentos de temperatura, precipitacion y demanda.

Preprocesado:

- Imputacion por mediana en variables numericas.
- Imputacion con `unknown` en categoricas.
- Escalado con `StandardScaler`.
- Encoding con `OneHotEncoder`.
- Dataset preparado con 99 features.

## 7. Division train/test

La division se hizo por meses completos para evitar fuga temporal.

- Train: 4562 filas, de 2015-10 a 2023-01.
- Test: 1196 filas, de 2023-02 a 2024-12.

No hay solape temporal entre entrenamiento y prueba.

## 8. Modelado

Modelos comparados:

- Random Forest Regressor.
- Extra Trees Regressor.
- HistGradientBoosting Regressor.
- XGBoost Regressor.

Metricas usadas:

- MAE.
- RMSE.
- R2.

Resultados principales:

| Modelo | RMSE | MAE | R2 |
|---|---:|---:|---:|
| ExtraTrees optimizado | 118515.718 | 47483.282 | 0.990 |
| ExtraTrees depth=10 | 119598.386 | 58741.780 | 0.990 |
| ExtraTrees depth=None | 121145.363 | 47611.640 | 0.990 |
| XGBoost depth=5 | 161776.414 | 65685.238 | 0.982 |
| RandomForest depth=None | 177393.055 | 63820.768 | 0.978 |

Modelo seleccionado: `ExtraTrees optimizado`.

Hiperparametros:

- `n_estimators=180`.
- `max_depth=None`.
- `min_samples_split=5`.
- `min_samples_leaf=1`.
- `max_features=1.0`.
- `bootstrap=True`.
- `random_state=42`.

El RMSE se usa como criterio principal porque penaliza mas los errores grandes, especialmente importantes en provincias o meses con mucho volumen turistico.

## 9. Evaluacion e interpretacion

Figuras disponibles para la presentacion:

- `reports/figures/predictions_vs_actual.png`.
- `reports/figures/residuals.png`.
- `reports/figures/monthly_actual_vs_predicted.png`.
- `reports/figures/feature_importance.png`.

La evaluacion no se limita a una metrica. Tambien se analizan predicciones frente a valores reales, residuos, evolucion temporal agregada e importancia de variables.

## 10. Fine-tuning costero e insular

Se entreno una variante especializada para 24 provincias costeras e insulares. En modelos tabulares clasicos, el fine-tuning se interpreta como reentrenamiento y ajuste de hiperparametros sobre un subconjunto especifico.

Protocolo:

- Train global: 4562 filas.
- Train costero: 2108 filas.
- Test costero comun: 552 filas.
- Validacion interna: 2021-08 a 2023-01.
- Test final: 2023-02 a 2024-12.

Comparacion:

| Modelo | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Global ExtraTrees | 79878.541 | 170759.091 | 0.988463 |
| Coastal ExtraTrees | 85369.661 | 171529.063 | 0.988359 |
| Tuned coastal ExtraTrees | 78121.147 | 156769.870 | 0.990276 |

Mejoras del modelo costero ajustado frente al global en el mismo test costero:

- RMSE mejora 8.19%.
- MAE mejora 2.20%.
- R2 sube de 0.988463 a 0.990276.

Limitacion:

El modelo costero mejora de forma agregada, pero no mejora todas las provincias. Reduce MAE en 13 de 24 provincias, por lo que debe tratarse como variante especializada y no como sustituto automatico del modelo global.

## 11. Despliegue en Hugging Face

El modelo seleccionado se exporta como pipeline completo y se publica en Hugging Face Hub.

Modelo:

```text
https://huggingface.co/HMartinezC/tourism-weather-model
```

Demo Gradio:

```text
https://huggingface.co/spaces/HMartinezC/tourism-weather-demo
```

La demo permite:

- Seleccionar provincia y mes.
- Cargar presets historicos de clima, calendario y movilidad.
- Obtener una prediccion de pernoctaciones hoteleras.
- Comparar el modelo global, el modelo costero ajustado y `amazon/chronos-2`.

Chronos-2 se usa como referencia de forecasting temporal. El modelo propio usa regresion tabular con variables explicativas, mientras que Chronos-2 usa el historico mensual de la provincia.

## 12. Conclusiones

Conclusiones principales:

- El proyecto cubre el ciclo completo de datos: ingesta, almacenamiento, transformacion, catalogacion, EDA, modelado, evaluacion y despliegue.
- La tabla final integra turismo, clima, calendario y movilidad en grano provincia-mes.
- El mejor modelo global fue ExtraTrees optimizado, con RMSE 118515.718, MAE 47483.282 y R2 0.990.
- La validacion temporal reduce el riesgo de fuga de informacion.
- El fine-tuning costero mejora el RMSE agregado un 8.19%, aunque no sustituye automaticamente al modelo global.
- La Space de Hugging Face convierte el modelo en una herramienta interactiva.

Mejoras futuras:

- Integrar movilidad terrestre si existe una fuente mensual y provincial defendible.
- Validar con varios cortes temporales.
- Crear una regla de seleccion por provincia entre modelo global y costero.
- Guardar logs de inferencia o resultados en RDS.
- Automatizar ingestas periodicas con Lambda si el proyecto evoluciona.

## Estructura recomendada de diapositivas

1. Titulo y objetivo del proyecto.
2. Problema de negocio y utilidad.
3. Fuentes de datos.
4. Arquitectura de datos.
5. Dataset final y calidad.
6. EDA y preparacion.
7. Split temporal y prevencion de fuga.
8. Modelos comparados y metricas.
9. Modelo final y visualizaciones.
10. Fine-tuning costero e insular.
11. Despliegue en Hugging Face y demo.
12. Conclusiones y mejoras futuras.

## Indicaciones para la presentacion generada

- Usar 10 a 12 diapositivas.
- Mantener bullets breves.
- Incluir notas de presentador.
- Incluir una diapositiva con diagrama de arquitectura.
- Incluir una tabla comparativa de modelos.
- Incluir una diapositiva especifica sobre fine-tuning.
- No inventar metricas ni resultados.
- Priorizar claridad sobre exceso de detalle.

