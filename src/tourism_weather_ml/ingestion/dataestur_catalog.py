from dataclasses import dataclass


@dataclass(frozen=True)
class DataesturEndpoint:
    endpoint: str
    name: str
    category: str
    priority: str
    reason: str


IDEAL_DATAESTUR_ENDPOINTS: tuple[DataesturEndpoint, ...] = (
    DataesturEndpoint(
        endpoint="EOH_PROV_DL",
        name="hotel_occupancy_by_province",
        category="alojamientos",
        priority="must",
        reason="Target principal: ocupacion, viajeros y pernoctaciones hoteleras por provincia.",
    ),
    DataesturEndpoint(
        endpoint="EOH_CCAA_DL",
        name="hotel_occupancy_by_region",
        category="alojamientos",
        priority="must",
        reason="Agregacion por CCAA para comparar con clima/festivos si provincia tiene demasiados nulos.",
    ),
    DataesturEndpoint(
        endpoint="FRONTUR_DL",
        name="international_arrivals",
        category="viajes",
        priority="high",
        reason="Demanda internacional; explica presion turistica de entrada.",
    ),
    DataesturEndpoint(
        endpoint="ETR_DL",
        name="resident_tourism",
        category="viajes",
        priority="high",
        reason="Demanda nacional de residentes, complementaria a FRONTUR.",
    ),
    DataesturEndpoint(
        endpoint="EGATUR_DL",
        name="international_tourist_spending",
        category="economia",
        priority="high",
        reason="Gasto turistico internacional; variable economica asociada a demanda.",
    ),
    DataesturEndpoint(
        endpoint="AENA_DESTINOS_DL",
        name="air_traffic",
        category="transporte",
        priority="medium",
        reason="Proxy de movilidad y conectividad con destinos.",
    ),
    DataesturEndpoint(
        endpoint="VALORES_CLIMATOLOGICOS_TEMPERATURA_DL",
        name="climate_temperature",
        category="sostenibilidad",
        priority="high",
        reason="Temperatura climatologica para relacion clima-demanda.",
    ),
    DataesturEndpoint(
        endpoint="VALORES_CLIMATOLOGICOS_PRECIPITACION_DL",
        name="climate_precipitation",
        category="sostenibilidad",
        priority="high",
        reason="Precipitacion climatologica; util para dias de lluvia y confort turistico.",
    ),
    DataesturEndpoint(
        endpoint="IND_RENTABILIDAD_PROVINCIA_DL",
        name="hotel_profitability_by_province",
        category="alojamientos_precios",
        priority="medium",
        reason="ADR/RevPAR y rentabilidad como contexto economico del alojamiento.",
    ),
)


IDEAL_DATAESTUR_ENDPOINT_NAMES = tuple(item.endpoint for item in IDEAL_DATAESTUR_ENDPOINTS)


def endpoint_name(endpoint: str) -> str:
    normalized = endpoint.strip().strip("/")
    for item in IDEAL_DATAESTUR_ENDPOINTS:
        if item.endpoint == normalized:
            return item.name
    return normalized.lower().removesuffix("_dl")
