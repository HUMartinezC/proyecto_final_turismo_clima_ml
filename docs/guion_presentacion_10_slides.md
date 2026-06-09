# Guion de apoyo - Presentacion Tourism Weather ML

Duracion objetivo: unos 15 minutos.

La idea no es memorizar palabra por palabra, sino quedarte con el hilo: problema, datos, arquitectura, preparacion, modelos, resultados, fine-tuning y despliegue.

## Diapositiva 1 - Titulo y objetivo

Tiempo aproximado: 1 minuto.

Guion:

Buenos dias. En esta presentacion voy a explicar el proyecto **Tourism Weather ML**, cuyo objetivo es predecir la demanda hotelera mensual en Espana combinando datos de turismo, clima, calendario y movilidad.

El problema se plantea como una regresion supervisada. La variable que queremos estimar es `hotel_overnights`, es decir, las pernoctaciones hoteleras mensuales. La unidad de analisis es una provincia en un mes concreto, por eso todo el dataset se construye alrededor de las variables `province + year_month`.

En este proyecto se intenta entrenar un modelo, construyendo un flujo completo: obtener datos de varias fuentes, integrarlos, analizarlos, entrenar modelos, evaluarlos y finalmente desplegar una demo funcional.

Transicion:

Empiezo explicando por que este problema tiene sentido y que utilidad puede tener.

## Diapositiva 2 - Problema y utilidad

Tiempo aproximado: 1 minuto.

Guion:

El objetivo principal es estimar cuantas pernoctaciones hoteleras puede haber en una provincia durante un mes determinado.

Esto puede ser util para anticipar picos o caidas de demanda turistica, comparar patrones entre provincias y entender mejor como influyen factores externos, como el clima, los festivos o la movilidad aeroportuaria.

Por ejemplo, una provincia costera puede tener una demanda muy marcada por la temporada alta, pero tambien puede verse afectada por el tiempo, por festivos concretos o por el volumen de pasajeros en aeropuertos cercanos.

Por eso el enfoque del proyecto es enriquecer el historico turistico con contexto externo, no limitarse solo a mirar la serie de pernoctaciones.

Transicion:

Para construir ese contexto, el proyecto integra varias fuentes de datos.

## Diapositiva 3 - Fuentes de datos

Tiempo aproximado: 1.5 minutos.

Guion:

El dataset final se construye a partir de cuatro fuentes principales.

La primera es **Dataestur**, que es la fuente clave porque aporta el target, `hotel_overnights`, ademas de variables turisticas como viajeros, estancia media u ocupacion.

La segunda es **Open-Meteo**, que se utiliza para obtener historico climatico diario. Esos datos se agregan a nivel mensual y provincial. Incluye variables como temperatura, precipitacion, lluvia y viento.

La tercera fuente es el paquete **holidays**, que permite generar festivos nacionales y autonomicos. Estos festivos se agregan por provincia y mes, porque el calendario puede afectar a la demanda turistica.

La cuarta fuente es **AENA**, que actua como proxy de movilidad aeroportuaria. Aporta pasajeros, operaciones, carga y numero de aeropuertos asociados a cada provincia.

Un reto importante aqui es que cada fuente viene con una granularidad distinta: unas son diarias, otras mensuales, unas estan por aeropuerto y otras por provincia. Por eso el trabajo de integracion es una parte esencial del proyecto.

Tambien se valoraron fuentes no integradas, como movilidad terrestre, Copernicus, OpenStreetMap o Google Trends. No se incorporaron porque no encajaban bien con el alcance, el grano temporal o la calidad necesaria.

Transicion:

Una vez definidas las fuentes, el siguiente paso fue organizarlas en una arquitectura reproducible.

## Diapositiva 4 - Arquitectura del pipeline

Tiempo aproximado: 1.5 minutos.

Guion:

La arquitectura combina ejecucion local con componentes cloud en AWS.

El procesamiento principal esta implementado en Python. El script central es `scripts/run_pipeline.py`, que permite ejecutar ingesta, procesamiento y catalogacion.

Los datos se organizan como un data lake por capas. La capa **bronze** conserva datos originales o lo mas cercanos posible a la fuente. La capa **silver** contiene tablas normalizadas por fuente. Finalmente, la capa **gold** integra todo en una tabla final preparada para EDA y Machine Learning.

En AWS, S3 funciona como almacenamiento del data lake. Glue Data Catalog registra las tablas externas, y Athena permite consultarlas con SQL sobre ficheros Parquet.

La parte final del flujo exporta el modelo y lo despliega en Hugging Face, separando el repositorio del modelo y la Space de Gradio.

La decision de usar este enfoque se debe a que el proyecto trabaja con fuentes historicas y batch. No hacia falta introducir una arquitectura en tiempo real; era mas importante que el flujo fuera reproducible, trazable y facil de volver a ejecutar.

Transicion:

El resultado de esa arquitectura es la tabla gold, que es la base del analisis y del entrenamiento.

## Diapositiva 5 - Dataset final y calidad

Tiempo aproximado: 1 minuto.

Guion:

La tabla final se llama `tourism_weather_monthly_features`.

Tiene 5772 filas, 31 columnas y cubre 52 provincias desde octubre de 2015 hasta diciembre de 2024. Cada fila representa una provincia en un mes.

Una comprobacion importante es que no hay duplicados por la clave `province + year_month`, lo cual valida que el grano esta correctamente construido.

Hay 14 filas sin target, es decir, sin `hotel_overnights`. Esas filas se mantienen como parte del dataset integrado, pero se excluyen del entrenamiento porque no se puede aprender una regresion sin variable objetivo.

Las variables quedan agrupadas en familias: turismo, clima, calendario, movilidad aeroportuaria y territorio. Esta mezcla es lo que permite que el modelo tenga mas contexto que una simple serie historica.

Transicion:

Antes de entrenar modelos, fue necesario analizar y preparar correctamente ese dataset.

## Diapositiva 6 - EDA y preparacion

Tiempo aproximado: 1.5 minutos.

Guion:

En la fase de EDA se revisaron columnas, tipos, nulos, duplicados, estadisticas descriptivas, outliers y correlaciones.

Una decision importante fue no eliminar automaticamente los outliers. En turismo, un valor extremo no siempre es un error: puede representar una provincia con mucha demanda, una temporada alta, un evento puntual o un destino especialmente turistico.

Tambien se tuvo cuidado con la fuga de informacion. Por ejemplo, variables como `hotel_travelers` estan muy relacionadas con el target. Pueden ser utiles para analisis, pero no se usan como predictores directos porque podrian hacer que el modelo pareciera mejor de lo que realmente seria en un escenario predictivo.

En cuanto al preprocesado, se aplico imputacion por mediana en numericas, imputacion con `unknown` en categoricas, escalado con `StandardScaler` y codificacion con `OneHotEncoder`.

Ademas, se crearon variables temporales como ano, mes, trimestre y temporada alta, junto con algunas transformaciones numericas. Tras todo el preprocesado, el dataset preparado quedo con 99 features.

Transicion:

Con los datos preparados, el siguiente punto clave es como se dividieron para entrenar y evaluar.

## Diapositiva 7 - Modelos comparados

Tiempo aproximado: 1.5 minutos.

Guion:

La division entre entrenamiento y test se hizo por meses completos. Esto es importante porque evita fuga temporal: el modelo entrena con datos hasta enero de 2023 y se evalua con datos posteriores, desde febrero de 2023 hasta diciembre de 2024.

El conjunto de entrenamiento tiene 4562 filas y el de test 1196 filas.

Se compararon varios modelos adecuados para regresion tabular: Random Forest, Extra Trees, HistGradientBoosting y XGBoost.

Las metricas usadas fueron MAE, RMSE y R2. El MAE mide el error absoluto medio, el RMSE penaliza mas los errores grandes y el R2 indica que proporcion de la variabilidad queda explicada por el modelo.

En este proyecto se prioriza el RMSE porque los errores grandes son especialmente relevantes. No es lo mismo fallar por poco en una provincia pequena que cometer un error muy alto en una provincia o mes con mucho volumen turistico.

Transicion:

Con esa comparacion, el modelo que mejor funciono fue ExtraTrees optimizado.

## Diapositiva 8 - Mejor modelo y resultados

Tiempo aproximado: 1.5 minutos.

Guion:

El mejor modelo global fue **ExtraTrees optimizado**.

En test obtuvo un RMSE de 118515.718, un MAE de 47483.282 y un R2 de 0.990.

Comparado con otras alternativas, ExtraTrees consiguio el menor RMSE. XGBoost y Random Forest tambien dan resultados razonables, pero quedan por detras en error.

Es importante no interpretar el R2 de forma aislada. Un R2 alto indica que el modelo captura bien la estructura general de los datos, pero por eso tambien se revisan MAE, RMSE, residuos, predicciones frente a valores reales e importancia de variables.

En las figuras de evaluacion se puede comprobar si las predicciones siguen bien los valores reales y si los residuos muestran algun patron preocupante.

La seleccion final se basa en rendimiento, estabilidad y coherencia con el objetivo predictivo.

Transicion:

Despues del modelo global, se hizo una prueba adicional especializada en provincias costeras e insulares.

## Diapositiva 9 - Fine-tuning costero e insular

Tiempo aproximado: 1.5 minutos.

Guion:

Como el proyecto utiliza modelos tabulares clasicos, el fine-tuning se plantea como una especializacion del entrenamiento: se reentrena y se ajustan hiperparametros sobre un subconjunto mas especifico.

En este caso se creo una variante para 24 provincias costeras e insulares, porque son territorios con patrones turisticos muy marcados y alta estacionalidad.

La comparacion se hizo de forma justa: el modelo global y el modelo costero se evaluaron sobre el mismo test costero.

El modelo global ExtraTrees obtuvo un RMSE de 170759.091 en ese test costero. El modelo costero ajustado bajo el RMSE a 156769.870 y subio el R2 a 0.990276.

Esto supone una mejora del RMSE del 8.19% y del MAE del 2.20%.

Pero hay una limitacion importante: la mejora es agregada, no universal. El modelo reduce MAE en 13 de 24 provincias. Por eso no debe sustituir automaticamente al modelo global, sino considerarse una variante especializada que podria usarse con una regla de seleccion por provincia.

Transicion:

Por ultimo, el proyecto no termina en el entrenamiento, sino que se despliega como una demo interactiva.

## Diapositiva 10 - Despliegue y conclusiones

Tiempo aproximado: 1.5 minutos.

Guion:

El modelo seleccionado se exporto como pipeline completo y se publico en Hugging Face Hub.

Ademas, se creo una demo con Gradio en Hugging Face Spaces. La aplicacion permite seleccionar provincia y mes, cargar valores historicos plausibles de clima, calendario y movilidad, y obtener una prediccion de pernoctaciones.

La demo tambien compara el modelo global, la variante costera ajustada y `amazon/chronos-2`, que se usa como referencia externa de forecasting temporal. La comparacion es metodologica: Chronos trabaja con el historico temporal, mientras que el modelo propio usa variables explicativas tabulares.

Como conclusion, el proyecto cubre el ciclo completo: integracion de fuentes, data lake, EDA, preparacion, modelado, evaluacion, fine-tuning y despliegue.

El mejor modelo global fue ExtraTrees optimizado. La validacion temporal ayuda a evitar fuga de informacion. Y el fine-tuning costero demuestra que puede haber valor en especializar modelos por segmentos, aunque con cuidado y validacion por provincia.

Como mejoras futuras, se podria incorporar movilidad terrestre, validar con varios cortes temporales, definir reglas para elegir entre modelo global y costero, y registrar inferencias en RDS.

Cierre:

En resumen, Tourism Weather ML no es solo un modelo predictivo, sino una solucion completa y reproducible para estimar demanda hotelera usando datos heterogeneos y despliegue interactivo.

