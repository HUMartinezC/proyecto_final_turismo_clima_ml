# Prompt para Gamma - Presentacion de 10 diapositivas

Crea una presentacion en espanol de exactamente 10 diapositivas sobre el proyecto **Tourism Weather ML**. La presentacion debe durar unos 15 minutos y servir para una defensa academica de un proyecto final de Machine Learning.

Estilo visual: profesional, tecnico, limpio, con diagramas simples, tablas pequenas y poco texto por diapositiva. No inventes datos. Usa los datos exactos de este documento.

## Diapositiva 1 - Titulo y objetivo

Titulo:

**Tourism Weather ML**

Subtitulo:

Prediccion de demanda hotelera mensual en Espana combinando turismo, clima, calendario y movilidad.

Contenido breve:

- Problema de regresion supervisada.
- Target: `hotel_overnights`.
- Unidad de analisis: provincia + mes.
- Rango temporal: 2015-10 a 2024-12.

Nota de presentador:

Presentar el proyecto como una solucion completa de datos y Machine Learning: desde fuentes externas hasta un modelo desplegado en Hugging Face.

## Diapositiva 2 - Problema y utilidad

Titulo:

**Problema de Machine Learning**

Contenido:

- Objetivo: estimar pernoctaciones hoteleras mensuales por provincia.
- Variable objetivo: `hotel_overnights`.
- Grano final: `province + year_month`.
- Utilidad: anticipar picos, caidas y patrones de demanda turistica.

Idea visual:

Usar un esquema simple:

```text
Provincia + Mes + Contexto externo -> Prediccion de pernoctaciones
```

Nota de presentador:

Explicar que el proyecto no solo mira historicos de turismo, sino que incorpora variables externas que pueden explicar la demanda.

## Diapositiva 3 - Fuentes de datos

Titulo:

**Datos integrados**

Usar esta tabla:

| Fuente | Papel | Grano original |
|---|---|---|
| Dataestur | Target y variables turisticas | Provincia/comunidad y mes |
| Open-Meteo | Clima historico | Coordenada y dia |
| holidays | Festivos nacionales y autonomicos | Region y dia |
| AENA | Movilidad aeroportuaria | Aeropuerto y mes |

Contenido adicional:

- Dataestur aporta `hotel_overnights`.
- Open-Meteo aporta temperatura, precipitacion, lluvia y viento.
- AENA aporta pasajeros, operaciones, carga y numero de aeropuertos.

Nota de presentador:

Resaltar que las fuentes tienen granularidades distintas y se integran en una tabla mensual por provincia.

## Diapositiva 4 - Arquitectura del pipeline

Titulo:

**Arquitectura de datos**

Crear un diagrama con este flujo:

```text
Fuentes externas
-> raw / S3 bronze
-> silver normalizado
-> gold integrado
-> EDA y entrenamiento
-> modelo exportado
-> Hugging Face Hub + Gradio Space
```

Componentes:

- Python para ETL y automatizacion.
- Amazon S3 como data lake.
- AWS Glue Data Catalog para tablas externas.
- Amazon Athena para consultas SQL sobre Parquet.
- Hugging Face para despliegue.

Nota de presentador:

Explicar que la arquitectura busca reproducibilidad local y trazabilidad en cloud mediante capas bronze, silver y gold.

## Diapositiva 5 - Dataset final y calidad

Titulo:

**Tabla gold: tourism_weather_monthly_features**

Metricas del dataset:

- 5772 filas.
- 31 columnas.
- 52 provincias.
- Rango: 2015-10 a 2024-12.
- 0 duplicados por `province + year_month`.
- 14 filas sin target, excluidas del entrenamiento.

Variables principales:

- Turismo.
- Clima.
- Calendario.
- Movilidad aeroportuaria.
- Territorio.

Idea visual:

Mostrar una tarjeta o bloque por cada familia de variables.

Nota de presentador:

Defender el grano provincia-mes como la clave que permite unir todas las fuentes.

## Diapositiva 6 - EDA y preparacion

Titulo:

**Preparacion para modelado**

Contenido:

- Revision de nulos, duplicados, tipos y outliers.
- Outliers conservados: pueden representar demanda turistica real.
- Variables con fuga, como `hotel_travelers`, no se usan como predictores directos.
- Split temporal por meses completos para evitar fuga de informacion.

Preprocesado:

- Imputacion por mediana en numericas.
- Imputacion con `unknown` en categoricas.
- `StandardScaler`.
- `OneHotEncoder`.
- Dataset preparado con 99 features.

Nota de presentador:

Explicar que se prioriza una evaluacion realista: no se mezcla informacion futura en entrenamiento.

## Diapositiva 7 - Modelos comparados

Titulo:

**Modelado y validacion**

Modelos:

- Random Forest Regressor.
- Extra Trees Regressor.
- HistGradientBoosting Regressor.
- XGBoost Regressor.

Split temporal:

- Train: 4562 filas, de 2015-10 a 2023-01.
- Test: 1196 filas, de 2023-02 a 2024-12.

Metricas:

- MAE.
- RMSE.
- R2.

Nota de presentador:

Indicar que RMSE se usa como criterio principal porque penaliza mas los errores grandes, relevantes en provincias o meses de alto volumen turistico.

## Diapositiva 8 - Mejor modelo y resultados

Titulo:

**Resultado principal: ExtraTrees optimizado**

Usar esta tabla:

| Modelo | RMSE | MAE | R2 |
|---|---:|---:|---:|
| ExtraTrees optimizado | 118515.718 | 47483.282 | 0.990 |
| ExtraTrees depth=10 | 119598.386 | 58741.780 | 0.990 |
| ExtraTrees depth=None | 121145.363 | 47611.640 | 0.990 |
| XGBoost depth=5 | 161776.414 | 65685.238 | 0.982 |
| RandomForest depth=None | 177393.055 | 63820.768 | 0.978 |

Modelo seleccionado:

- `ExtraTrees optimizado`.
- Mejor RMSE en test temporal.
- Buen equilibrio entre error absoluto y ajuste global.

Nota de presentador:

Comentar que el R2 es alto, pero se interpreta junto a MAE, RMSE y analisis de residuos.

## Diapositiva 9 - Fine-tuning costero e insular

Titulo:

**Especializacion para provincias costeras**

Contexto:

- Se entreno una variante para 24 provincias costeras e insulares.
- El fine-tuning en este proyecto equivale a reentrenar y ajustar hiperparametros sobre un subconjunto especifico.

Usar esta tabla:

| Modelo | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Global ExtraTrees | 79878.541 | 170759.091 | 0.988463 |
| Coastal ExtraTrees | 85369.661 | 171529.063 | 0.988359 |
| Tuned coastal ExtraTrees | 78121.147 | 156769.870 | 0.990276 |

Resultado:

- RMSE mejora 8.19%.
- MAE mejora 2.20%.
- R2 sube a 0.990276.

Limitacion:

- Mejora agregada, pero no en todas las provincias.
- Reduce MAE en 13 de 24 provincias.

Nota de presentador:

Presentar el modelo costero como variante especializada, no como sustituto automatico del modelo global.

## Diapositiva 10 - Despliegue y conclusiones

Titulo:

**Despliegue y cierre**

Despliegue:

- Modelo publicado en Hugging Face Hub.
- Demo interactiva en Hugging Face Spaces con Gradio.
- Comparacion con `amazon/chronos-2` como referencia de forecasting.

URLs:

```text
Modelo: https://huggingface.co/HMartinezC/tourism-weather-model
Space: https://huggingface.co/spaces/HMartinezC/tourism-weather-demo
```

Conclusiones:

- Pipeline completo: ingesta, data lake, EDA, modelado, evaluacion y despliegue.
- Mejor modelo global: ExtraTrees optimizado.
- Validacion temporal para evitar fuga de informacion.
- Fine-tuning costero mejora RMSE agregado.

Mejoras futuras:

- Integrar movilidad terrestre.
- Validar con varios cortes temporales.
- Crear reglas por provincia para elegir modelo global o costero.
- Registrar inferencias en RDS.

Nota de presentador:

Cerrar destacando que el proyecto demuestra una solucion integral, reproducible y desplegada, no solo un notebook de entrenamiento.

