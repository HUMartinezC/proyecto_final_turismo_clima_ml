from dataclasses import dataclass


@dataclass(frozen=True)
class DataSource:
    name: str
    domain: str
    grain: str
    mandatory_for_mvp: bool
    target: str
    reason: str


IDEAL_SOURCES: tuple[DataSource, ...] = (
    DataSource(
        name="dataestur",
        domain="tourism",
        grain="month_region",
        mandatory_for_mvp=True,
        target="s3_bronze_and_documentdb",
        reason="Fuente mas directa para demanda turistica agregada y variables de alojamiento/gasto.",
    ),
    DataSource(
        name="aemet",
        domain="weather",
        grain="day_station",
        mandatory_for_mvp=True,
        target="s3_bronze_and_documentdb",
        reason="Clima oficial en Espana; aporta temperatura, lluvia, viento y eventos extremos.",
    ),
    DataSource(
        name="holidays",
        domain="calendar",
        grain="day_region",
        mandatory_for_mvp=True,
        target="s3_bronze_and_rds",
        reason="Captura festivos, puentes y estacionalidad, variables muy explicativas para turismo.",
    ),
    DataSource(
        name="aena",
        domain="mobility",
        grain="month_airport",
        mandatory_for_mvp=False,
        target="s3_bronze_and_rds",
        reason="Proxy de movilidad aeroportuaria; util para mejorar el modelo tras el MVP.",
    ),
)
