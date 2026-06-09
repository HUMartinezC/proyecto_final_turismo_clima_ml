# Brief para generar una presentacion de 15 minutos

Quiero que crees una presentacion profesional, clara y defendible sobre el proyecto **Tourism Weather ML**. La presentacion debe durar aproximadamente **15 minutos** y estar pensada para una defensa academica/tecnica de un proyecto final de Machine Learning aplicado a turismo, clima y datos en la nube.

## Objetivo de la presentacion

Explicar de forma ordenada el problema, las fuentes de datos, la arquitectura, el proceso de preparacion, el modelado, los resultados, el fine-tuning y el despliegue final.

La presentacion debe transmitir tres ideas principales:

- El proyecto resuelve un problema realista de regresion: estimar la demanda hotelera mensual por provincia en Espana.
- El valor no esta solo en el modelo, sino en construir un pipeline reproducible que integra turismo, clima, calendario y movilidad.
- El resultado final incluye evaluacion, comparacion, especializacion para provincias costeras e insulares y despliegue funcional en Hugging Face.

## Estilo esperado

- Idioma: espanol.
- Duracion: 15 minutos.
- Tono: tecnico, seguro y didactico.
- Audiencia: tribunal o profesores con conocimientos de datos, cloud y Machine Learning.
- Formato recomendado: 10 a 12 diapositivas.
- Evitar diapositivas saturadas. Priorizar narrativa, diagramas, tablas pequenas y visualizaciones.
- Incluir notas de presentador breves para cada diapositiva.

## Datos clave del proyecto

Nombre del proyecto:

```text
Tourism Weather ML
```

Problema:

```text
Regresion supervisada para estimar pernoctaciones hoteleras mensuales por provincia en Espana.
```

Variable objetivo:

```text
hotel_overnights
```

Grano del dataset final:

```text
province + year_month
```

Tabla final:

```text
tourism_weather_monthly_features
```

Rango temporal:

```text
2015-10 a 2024-12
```

Resumen del dataset gold:

- 5772 filas.
- 31 columnas.
- 52 provincias.
- 0 duplicados por `province + year_month`.
- 14 filas sin `hotel_overnights`, excluidas del entrenamiento.

Split temporal:

- Train: 4562 filas, de 2015-10 a 2023-01.
- Test: 1196 filas, de 2023-02 a 2024-12.
- No hay solape temporal entre entrenamiento y prueba.

## Fuentes de datos

Usar estas fuentes en una diapositiva de tabla o diagrama:

| Fuente | Papel en el proyecto | Grano original |
|---|---|---|
| Dataestur | Target y variables turisticas: pernoctaciones, viajeros, estancia media y ocupacion | Provincia/comunidad y mes |
| Open-Meteo | Variables climaticas historicas diarias agregadas a mes | Coordenada y dia |
| holidays | Festivos nacionales y autonomicos | Region y dia |
| AENA | Proxy de movilidad aeroportuaria: pasajeros, operaciones, carga y aeropuertos | Aeropuerto y mes |

Fuente principal del target:

```text
Dataestur - endpoint EOH_PROV_DL
```

Variables climaticas principales:

- Temperatura media, maxima y minima.
- Precipitacion.
- Lluvia.
- Horas de precipitacion.
- Viento medio y maximo.

Variables de calendario:

- Festivos nacionales.
- Festivos autonomicos.
- Total de festivos.
- Mes, trimestre y temporada alta.

Variables de movilidad:

- Pasajeros AENA.
- Operaciones AENA.
- Carga en kg.
- Numero de aeropuertos por provincia.

Fuentes descartadas o no integradas:

- Movilidad terrestre: candidata futura si se encuentra una fuente mensual y territorialmente compatible.
- Copernicus ERA5: potente, pero Open-Meteo era suficiente para el alcance.
- OpenStreetMap: util para features geoespaciales, pero no imprescindible.
- Google Trends/redes sociales: mas ruido, sesgos y dependencias externas.

## Arquitectura

Explicar que se implemento una arquitectura reproducible local y cloud.

Componentes:

- Python como motor ETL.
- Amazon S3 como data lake por capas.
- AWS Glue Data Catalog para registrar tablas externas.
- Amazon Athena para consultar Parquet en S3 con SQL.
- Amazon RDS MariaDB preparado para pruebas o resultados estructurados.
- AWS Lambda preparado como automatizacion opcional.
- Hugging Face Hub y Spaces para el despliegue final.

Capas del data lake:

```text
bronze: datos originales y manifests
silver: tablas normalizadas por fuente
gold: tabla integrada para EDA y Machine Learning
```

Flujo recomendado para el diagrama:

```text
Dataestur / Open-Meteo / holidays / AENA
        -> raw / S3 bronze
        -> silver normalizado
        -> gold tourism_weather_monthly_features
        -> notebooks y entrenamiento
        -> modelo exportado
        -> Hugging Face Hub + Gradio Space
```

Comando principal:

```bash
python scripts/run_pipeline.py
```

Otros comandos utiles:

```bash
python scripts/run_pipeline.py --dry-run
python scripts/run_pipeline.py --process --skip-s3-upload
python scripts/run_pipeline.py --catalog
```

## Preparacion y EDA

Incluir una diapositiva sobre calidad de datos y decisiones de preparacion.

Analisis realizado:

- Inspeccion inicial de registros.
- Revision de tipos, nulos, valores unicos y duplicados.
- Estadisticas descriptivas: media, mediana, moda, desviacion estandar y percentiles.
- Deteccion de outliers con IQR.
- Histogramas, dispersiones, boxplots y mapa de correlaciones.
- Analisis de correlacion entre target y variables explicativas.

Decisiones importantes:

- Las filas sin target se excluyen del entrenamiento.
- Los outliers no se eliminan automaticamente porque pueden representar demanda turistica real.
- Variables con riesgo de fuga, como `hotel_travelers`, se reservan para analisis y no se usan como predictor directo.
- El split se hace por meses completos para evitar fuga temporal.

Transformaciones:

- `year`, `month`, `quarter`, `is_high_season`.
- `hotel_overnights_log1p`.
- `aena_passengers_log1p`.
- `precipitation_sqrt`.
- `temperature_2m_mean_sq`.
- Buckets interpretables de temperatura, precipitacion y demanda.

Preprocesado:

- Imputacion por mediana en numericas.
- Imputacion con `unknown` en categoricas.
- Escalado con `StandardScaler`.
- Encoding con `OneHotEncoder`.
- Dataset preparado con 99 features.

## Modelado

Crear una diapositiva de comparacion de modelos.

Modelos entrenados:

- Random Forest Regressor.
- Extra Trees Regressor.
- HistGradientBoosting Regressor.
- XGBoost Regressor.

Metricas:

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
| XGBoost shallow | 176416.970 | 84567.447 | 0.978 |
| HistGradientBoosting shallow | 176941.497 | 70580.243 | 0.978 |
| RandomForest depth=None | 177393.055 | 63820.768 | 0.978 |
| HistGradientBoosting deep | 177789.146 | 71544.613 | 0.978 |
| RandomForest depth=8 | 181992.707 | 78162.984 | 0.977 |

Modelo seleccionado:

```text
ExtraTrees optimizado
```

Hiperparametros:

```text
n_estimators=180
max_depth=None
min_samples_split=5
min_samples_leaf=1
max_features=1.0
bootstrap=True
random_state=42
```

Justificacion:

- Es el modelo con menor RMSE en test temporal.
- Mantiene un R2 alto: 0.990.
- RMSE se usa como criterio principal porque penaliza mas los errores grandes, importantes en provincias o meses de alto volumen turistico.

## Visualizaciones recomendadas

Usar las figuras disponibles en `reports/figures/`:

- `predictions_vs_actual.png`: predicciones frente a valores reales.
- `residuals.png`: analisis de residuos.
- `monthly_actual_vs_predicted.png`: evolucion mensual agregada real frente a predicha.
- `feature_importance.png`: importancia de variables.
- `coastal_model_metrics.png`: comparacion del modelo costero.
- `coastal_monthly_predictions.png`: predicciones mensuales costeras.

Recomendacion:

- No incluir todas si no caben.
- Priorizar `predictions_vs_actual.png`, `monthly_actual_vs_predicted.png`, `feature_importance.png` y una figura del fine-tuning costero.

## Fine-tuning costero e insular

Dedicar una diapositiva a la especializacion del modelo.

Idea principal:

El proyecto usa modelos tabulares clasicos, por lo que el equivalente practico al fine-tuning consiste en reentrenar y reajustar hiperparametros sobre un subconjunto mas especifico.

Segmento:

```text
24 provincias costeras e insulares
```

Ejemplos:

- Alicante.
- Barcelona.
- Cadiz.
- Illes Balears.
- Las Palmas.
- Malaga.
- Santa Cruz de Tenerife.
- Valencia.

Protocolo:

- Train global: 4562 filas.
- Train costero: 2108 filas.
- Test costero comun: 552 filas.
- Validacion interna: 2021-08 a 2023-01.
- Test: 2023-02 a 2024-12.
- Seleccion por menor RMSE de validacion.

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

Limitacion importante:

El modelo costero ajustado mejora de forma agregada, pero no mejora todas las provincias. Reduce MAE en 13 de 24 provincias, por lo que debe tratarse como variante especializada y no como sustituto automatico del modelo global.

## Despliegue y demo

Incluir una diapositiva final de producto/despliegue.

Modelo publicado:

```text
https://huggingface.co/HMartinezC/tourism-weather-model
```

Space Gradio:

```text
https://huggingface.co/spaces/HMartinezC/tourism-weather-demo
```

Script de exportacion:

```bash
python scripts/train_export_model.py
```

Script de despliegue:

```bash
python scripts/deploy_to_huggingface.py
```

La demo permite:

- Seleccionar provincia y mes.
- Introducir o cargar presets historicos de clima, calendario y movilidad.
- Obtener una prediccion de pernoctaciones hoteleras.
- Comparar modelo global, modelo costero ajustado y `amazon/chronos-2`.
- Ver un historial local de las ultimas predicciones de la sesion.

Comparacion con Hugging Face:

- `amazon/chronos-2` se usa como referencia de forecasting de series temporales.
- Chronos-2 recibe historico mensual con columnas `item_id`, `timestamp` y `target`.
- La comparacion es metodologica: forecasting temporal frente a regresion tabular con variables explicativas.

## Estructura sugerida de diapositivas

### 1. Titulo y objetivo

Titulo:

```text
Tourism Weather ML: prediccion de demanda hotelera con turismo, clima y movilidad
```

Contenido:

- Problema de regresion supervisada.
- Target: `hotel_overnights`.
- Ambito: provincias espanolas, meses de 2015-10 a 2024-12.

Nota de presentador:

Presentar el proyecto como una solucion completa: datos, arquitectura, modelo y despliegue.

Tiempo: 1 minuto.

### 2. Problema y utilidad

Contenido:

- Estimar demanda hotelera mensual por provincia.
- Ayuda a anticipar picos, caidas y patrones estacionales.
- Integra clima, calendario y movilidad como explicadores.

Nota de presentador:

Explicar por que no basta con mirar historicos: se busca enriquecer la prediccion con contexto externo.

Tiempo: 1 minuto.

### 3. Fuentes de datos

Contenido:

- Tabla con Dataestur, Open-Meteo, holidays y AENA.
- Indicar que todas convergen al grano `province + year_month`.
- Mencionar fuentes descartadas y por que.

Nota de presentador:

Resaltar que cada fuente aporta una parte distinta del comportamiento turistico.

Tiempo: 1.5 minutos.

### 4. Arquitectura de datos

Contenido:

- Diagrama bronze, silver, gold.
- S3, Glue, Athena y Python.
- Script unico `scripts/run_pipeline.py`.

Nota de presentador:

Explicar que el pipeline es reproducible localmente y trasladable a AWS.

Tiempo: 1.5 minutos.

### 5. Dataset final y calidad

Contenido:

- 5772 filas, 31 columnas, 52 provincias.
- 0 duplicados.
- 14 filas sin target excluidas del entrenamiento.
- Rango 2015-10 a 2024-12.

Nota de presentador:

Defender el grano del dataset y la importancia de validar la clave `province + year_month`.

Tiempo: 1 minuto.

### 6. EDA y preparacion

Contenido:

- Nulos, duplicados, outliers, correlaciones.
- Outliers conservados por ser demanda real.
- Variables con fuga excluidas.
- Split temporal.

Nota de presentador:

Subrayar que la preparacion evita conclusiones demasiado optimistas por fuga temporal o variables directamente ligadas al target.

Tiempo: 1.5 minutos.

### 7. Modelos comparados

Contenido:

- Random Forest, Extra Trees, HistGradientBoosting y XGBoost.
- Metricas: MAE, RMSE y R2.
- Tabla resumida de resultados.

Nota de presentador:

Explicar que se comparan enfoques robustos para datos tabulares y que RMSE se prioriza por errores grandes.

Tiempo: 1.5 minutos.

### 8. Modelo final y resultados

Contenido:

- Modelo: ExtraTrees optimizado.
- MAE: 47483.282.
- RMSE: 118515.718.
- R2: 0.990.
- Visual: real vs predicho o serie mensual agregada.

Nota de presentador:

Explicar el rendimiento y comentar visualmente si las predicciones siguen la estructura temporal agregada.

Tiempo: 1.5 minutos.

### 9. Interpretabilidad y errores

Contenido:

- Importancia de variables.
- Residuos.
- Comentar posibles errores en provincias/meses de alta demanda.

Nota de presentador:

Mostrar que no solo se reporta una metrica, sino que se analiza el comportamiento del modelo.

Tiempo: 1 minuto.

### 10. Fine-tuning costero

Contenido:

- 24 provincias costeras e insulares.
- Comparacion global vs costero vs costero ajustado.
- RMSE mejora 8.19%, MAE mejora 2.20%.
- Limitacion: mejora 13 de 24 provincias.

Nota de presentador:

Presentar el fine-tuning como una especializacion util, pero con criterio: no reemplaza automaticamente al modelo global.

Tiempo: 1.5 minutos.

### 11. Despliegue y comparacion externa

Contenido:

- Hugging Face Model Hub.
- Space Gradio.
- Comparacion con `amazon/chronos-2`.
- Presets historicos por provincia y mes.

Nota de presentador:

Explicar que la demo convierte el modelo en una herramienta usable y que Chronos-2 sirve como referencia metodologica.

Tiempo: 1.5 minutos.

### 12. Conclusiones y mejoras futuras

Contenido:

- Pipeline completo de datos a despliegue.
- Mejor modelo: ExtraTrees optimizado.
- Fine-tuning costero mejora RMSE agregado.
- Futuras mejoras: movilidad terrestre, validacion temporal con mas cortes, reglas de seleccion por provincia, logging de inferencias en RDS.

Nota de presentador:

Cerrar enfatizando que el proyecto cubre el ciclo completo: fuentes, arquitectura, EDA, ML, evaluacion, comparacion y despliegue.

Tiempo: 1 minuto.

## Mensajes que deben quedar claros

- El target procede de Dataestur y representa pernoctaciones hoteleras.
- La unidad de analisis es provincia-mes.
- Se evito fuga temporal mediante split por meses completos.
- El mejor modelo global fue ExtraTrees optimizado.
- El R2 alto debe interpretarse junto a MAE, RMSE y analisis de residuos.
- El fine-tuning costero mejora metricas agregadas, pero tiene limitaciones provinciales.
- La arquitectura usa S3, Glue y Athena para organizar y consultar el data lake.
- La demo en Hugging Face demuestra que el modelo se puede consumir de forma interactiva.

## Requisitos para la IA generadora

Genera:

- Una presentacion de 10 a 12 slides.
- Titulos claros y tecnicos.
- Bullets breves por slide.
- Notas de presentador por slide.
- Sugerencias visuales concretas.
- Una diapositiva con diagrama de arquitectura.
- Una diapositiva con tabla comparativa de modelos.
- Una diapositiva sobre fine-tuning costero.
- Una diapositiva final de conclusiones y trabajo futuro.

No inventes resultados no indicados en este briefing. Si necesitas simplificar, conserva los valores de metricas, el rango temporal, el grano del dataset y las URLs de despliegue.
