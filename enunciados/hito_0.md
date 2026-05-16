# Hito 0

En este hito sentaréis las bases del proyecto. Debéis definir el problema de Machine Learning que vais a resolver, justificar la selección de datos y construir la arquitectura de ingesta y almacenamiento que dará soporte al resto del proyecto.

## Notebook requerido

Debéis entregar un notebook que incluya:

- Definición del problema de Machine Learning (clasificación, regresión, clustering, etc.)
- Descripción del contexto del problema y su utilidad real
- Identificación y justificación de las variables relevantes
- Definición clara de:
	- Variable objetivo (target)
	- Variables independientes (features)
	- Tipo de problema: supervisado / no supervisado

Además, debéis obtener los datos según las variables definidas e integrar información proveniente de múltiples fuentes con diferente estructura.

## Script requerido

Se desarrollará un script que sea capaz de:

- Desplegar la arquitectura de datos
- Ingestar los datos
- Procesar y unificar la información

## Arquitectura de datos y almacenamiento

La arquitectura debe integrar todas las fuentes en un repositorio único. Debéis justificar la elección del sistema de almacenamiento utilizado.

Opciones tecnológicas:

- ETL/ELT: Apache NiFi, AWS Glue o Amazon Athena
- Servicios AWS (boto3): Amazon S3, Amazon RDS, AWS Lambda
- Base de datos NoSQL: MongoDB Atlas o Amazon DocumentDB
- Procesamiento en tiempo real: Apache Kafka

## Entregables

- Documento o notebook con la descripción del problema, variables seleccionadas y justificación
- Script único funcional (despliegue + ingesta + procesamiento)
- Justificación técnica del sistema de almacenamiento elegido