# Proyecto de Curso: Desarrollo de un Sistema Completo de Machine Learning

El objetivo de este proyecto es desarrollar un sistema completo de Machine Learning que abarque desde la obtención de datos hasta el despliegue y mejora de un modelo, utilizando tecnologías modernas de procesamiento de datos, almacenamiento y modelado.

## 1. Visión del problema y selección de variables

El alumnado deberá:

- Definir un problema de Machine Learning realista (clasificación, regresión, clustering, etc.).
- Describir el contexto del problema y su utilidad.
- Identificar las variables relevantes que influyen en el problema.
- Justificar la selección de dichas variables.
- Definir claramente:
  - Variable objetivo (target).
  - Variables independientes (features).
  - Tipo de problema (supervisado / no supervisado).

## 2. Obtención y almacenamiento de los datos

### Requisitos:

- Obtener los datos según las variables seleccionadas en el apartado anterior.
- Integrar datos provenientes de múltiples fuentes con diferente estructura.
- Diseñar una arquitectura de datos que integre todas las fuentes en un repositorio único.
- Justificar la elección del sistema de almacenamiento
- Todo el sistema de ingestión, procesamiento y almacenamiento debe poder ejecutarse mediante un único script que:
  - Despliegue la arquitectura.
  - Ingestione los datos.
  - Procese y unifique la información.

### Tecnologías obligatorias:

- Uso de herramientas ETL/ELT como:
  - Apache NiFi
  - AWS Glue
  - Amazon Athena

- Uso de servicios AWS mediante `boto3`:
  - Amazon S3 para almacenamiento de datos.
  - Amazon RDS para datos estructurados.
  - AWS Lambda para automatización de procesos.

- Uso de bases de datos NoSQL:
  - MongoDB Atlas o Amazon DocumentDB.

- Procesamiento de datos en tiempo real:
  - Apache Kafka.

## 3. Análisis Exploratorio de Datos (EDA)

Realizar un análisis exploratorio completo que incluya al menos lo siguiente:

- Inspección inicial:
  - Mostrar los primeros 5 registros de cada dataset
  - Análisis del contenido de cada columna

- Estadísticas descriptivas:
  - Media
  - Mediana
  - Moda
  - Desviación estándar
  - Percentiles

- Identificación de patrones, anomalías o valores atípicos

- Visualización de datos utilizando las gráficas más adecuadas:
  - Histogramas
  - Diagramas de dispersión
  - Boxplots
  - Gráficos de correlación
  - Etcétera

- Análisis de correlaciones entre variables

## 4. Preparación del conjunto de datos

### Integración de datos
- Unificación de múltiples datasets
- Resolución de inconsistencias:
  - Tipos de datos
  - Duplicados
  - Conflictos entre fuentes

### Limpieza de datos:

- Eliminación de variables irrelevantes:
  - Basado en correlación o criterio experto

- Manejo de valores faltantes:
  - Imputación (media, mediana, moda, cero, etc.).
  - Eliminación de filas/columnas si procede

- Tratamiento de valores duplicados

- Tratamiento de valores atípicos:
  - Eliminación o corrección

- Adecuación de los tipos de datos

- Gestión de inconsistencias

### Ingeniería de características:

- Discretización de variables continuas.
- Descomposición de variables:
  - Fechas (día, mes, año, hora).
  - Variables categóricas complejas.
- Transformaciones:
  - log(x)
  - sqrt(x)
  - x²
- Creación de nuevas variables combinadas.
- Escalado de características:
  - Normalización o estandarización.
- Encoding de variables categóricas:
  - Label Encoding
  - One-Hot Encoding
  - Embedding

### División del dataset:

- Separar en:
  - Entrenamiento (80%)
  - Test (20%)

## 5. Creación y entrenamiento del modelo

- Implementar al menos **dos modelos diferentes** vistos en clase con distintas combinaciones de parámetros cada uno de ellos (pipeline, GridSearchCV).
- Entrenar ambos modelos con el conjunto de entrenamiento.
- Documentar:
  - Justificación de la elección de los modelos.
  - Arquitectura del modelo (si aplica).
  - Parámetros que optimizan los resultados en cada modelo.

## 6. Validación del modelo

- Evaluar los modelos utilizando métricas adecuadas según el tipo de problema:
  - Clasificación: accuracy, precision, recall, F1-score, ROC-AUC.
  - Regresión: MAE, MSE, RMSE, R².

- Ajustar hiperparámetros de los modelos.
- Comparar resultados entre modelos.
- Seleccionar el modelo con mejor rendimiento.

## 7. Representación gráfica del modelo

- Visualizar el comportamiento del modelo:
  - Predicciones vs valores reales.
  - Curvas de aprendizaje.
  - Matrices de confusión (si aplica).
  - Importancia de variables.

- Diferenciar claramente:
  - Datos originales.
  - Predicciones del modelo.

## 8. Pruebas, despliegue y mejora del modelo

### Despliegue:

- Subir el modelo a Hugging Face Hub.
- Crear una aplicación utilizando Gradio que permita:
  - Introducir nuevos datos.
  - Obtener predicciones en tiempo real.

### Comparación:

- Comparar el modelo propio con otros modelos disponibles en Hugging Face.

### Fine-tuning:

- Realizar fine-tuning del modelo utilizando un dataset más específico.
- Documentar mejoras obtenidas tras el ajuste.

## Entregables

El proyecto deberá incluir:

- Código fuente completo y organizado en un repositorio en GitHub.
- Para cada hito se deberá indicar el commit o tag correspondiente, por ejemplo hito-1, hito-2, etc.
- Script único que despliegue la arquitectura de datos y procese la información.
- Todo script, módulo, fichero de configuración, notebook, documentación o recurso necesario para reproducir el trabajo deberá estar incluido en el repositorio.
- En cada hito deberéis entregar un notebook explicativo donde se describa qué se ha hecho, qué scripts se ejecutan, qué resultados se obtienen y qué decisiones técnicas se han tomado.
- Modelos entrenados.
- Aplicación Gradio funcional.
- Documentación técnica del proyecto.
- Justificación de decisiones técnicas.
- Presentación para explicar el proyecto al profesorado dónde se explique el proyecto con un tiempo disponible de 20 minutos.

#### Propuesta orientativa de estructura

```text
PFC/
├── datasets/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── notebooks/
│   ├── hito_01_vision_problema.ipynb
│   ├── hito_02_obtencion_almacenamiento.ipynb
│   ├── hito_03_eda.ipynb
│   ├── hito_04_preparacion_datos.ipynb
│   └── hito_05_modelado_validacion.ipynb
├── scripts/
│   ├── run_pipeline.py
│   └── run_demo.ps1
├── src/
│   ├── aws/
│   ├── kafka/
│   ├── spark/
│   ├── preprocessing/
│   ├── training/
│   └── app/
├── models/
├── docs/
│   ├── arquitectura.md
│   ├── decisiones_tecnicas.md
│   ├── preparacion_datos.md
│   └── despliegue.md
├── logs/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Evaluación

Se valorará:

- Complejidad y coherencia de la solución.
- Correcta integración de tecnologías.
- Calidad del análisis exploratorio.
- Justificación de decisiones.
- Rendimiento de los modelos.
- Originalidad del enfoque.
- Correcta implementación del pipeline completo de datos.
- Funcionamiento del despliegue y la aplicación final.
- Calidad de la presentación