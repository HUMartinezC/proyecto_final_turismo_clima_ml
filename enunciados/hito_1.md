# Hito 1

En este hito se trata de abordar los siguientes apartados del proyecto, segun las especificaciones que se detallan en el mismo.

## 3. Analisis Exploratorio de Datos (EDA)

Realizar un analisis exploratorio completo que incluya al menos lo siguiente:

### Inspeccion inicial

- Mostrar los primeros 5 registros de cada dataset.
- Analisis del contenido de cada columna.

### Estadisticas descriptivas

- Media.
- Mediana.
- Moda.
- Desviacion estandar.
- Percentiles.

### Patrones, anomalias y valores atipicos

- Identificacion de patrones relevantes.
- Identificacion de anomalias.
- Identificacion de valores atipicos.

### Visualizacion de datos

Utilizar las graficas mas adecuadas, incluyendo cuando proceda:

- Histogramas.
- Diagramas de dispersion.
- Boxplots.
- Graficos de correlacion.
- Otras visualizaciones relevantes.

### Correlaciones

- Analisis de correlaciones entre variables.

## 4. Preparacion del conjunto de datos

### Integracion de datos

- Unificacion de multiples datasets.
- Resolucion de inconsistencias:
  - Tipos de datos.
  - Duplicados.
  - Conflictos entre fuentes.

### Limpieza de datos

- Eliminacion de variables irrelevantes, fundamentada en correlacion u otro criterio a justificar.
- Manejo de valores faltantes:
  - Imputacion: media, mediana, moda, cero, etc.
  - Eliminacion de filas o columnas si procede.
- Tratamiento de valores duplicados.
- Tratamiento de valores atipicos:
  - Eliminacion o correccion.
- Adecuacion de los tipos de datos.
- Gestion de inconsistencias.

### Ingenieria de caracteristicas

- Discretizacion de variables continuas.
- Descomposicion de variables:
  - Fechas: dia, mes, ano, hora.
  - Variables categoricas complejas.
- Transformaciones:
  - `log(x)`.
  - `sqrt(x)`.
  - `x²`.
- Creacion de nuevas variables combinadas.
- Escalado de caracteristicas:
  - Normalizacion o estandarizacion.
- Encoding de variables categoricas:
  - Label Encoding.
  - One-Hot Encoding.
  - Embedding.

### Division del dataset

Separar el conjunto de datos en:

- Entrenamiento: 80%.
- Test: 20%.
