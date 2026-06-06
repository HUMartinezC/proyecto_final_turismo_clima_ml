from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path

import gradio as gr
import joblib
import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download


GLOBAL_MODEL_FILENAME = "tourism_weather_extra_trees.joblib"
GLOBAL_METADATA_FILENAME = "model_metadata.json"
COASTAL_MODEL_FILENAME = "tourism_weather_coastal_extra_trees.joblib"
COASTAL_METADATA_FILENAME = "coastal_model_metadata.json"
CHRONOS_CONTEXT_FILENAME = "chronos_context.csv"
CHRONOS_MODEL_ID = "amazon/chronos-2"
HISTORY_COLUMNS = [
    "Provincia",
    "Comunidad autónoma",
    "Fecha",
    "Modelo global",
    "Modelo costero ajustado",
    "Modelo HF Chronos-2",
    "Diferencia",
]

PROVINCE_REGION_CODES = {
    "A Coruna": "GA",
    "Alava": "PV",
    "Albacete": "CM",
    "Alicante": "VC",
    "Almeria": "AN",
    "Asturias": "AS",
    "Avila": "CL",
    "Badajoz": "EX",
    "Barcelona": "CT",
    "Bizkaia": "PV",
    "Burgos": "CL",
    "Caceres": "EX",
    "Cadiz": "AN",
    "Cantabria": "CB",
    "Castellon": "VC",
    "Ceuta": "CE",
    "Ciudad Real": "CM",
    "Cordoba": "AN",
    "Cuenca": "CM",
    "Gipuzkoa": "PV",
    "Girona": "CT",
    "Granada": "AN",
    "Guadalajara": "CM",
    "Huelva": "AN",
    "Huesca": "AR",
    "Illes Balears": "IB",
    "Jaen": "AN",
    "La Rioja": "RI",
    "Las Palmas": "CN",
    "Leon": "CL",
    "Lleida": "CT",
    "Lugo": "GA",
    "Madrid": "MD",
    "Malaga": "AN",
    "Melilla": "ML",
    "Murcia": "MC",
    "Navarra": "NC",
    "Ourense": "GA",
    "Palencia": "CL",
    "Pontevedra": "GA",
    "Salamanca": "CL",
    "Santa Cruz de Tenerife": "CN",
    "Segovia": "CL",
    "Sevilla": "AN",
    "Soria": "CL",
    "Tarragona": "CT",
    "Teruel": "AR",
    "Toledo": "CM",
    "Valencia": "VC",
    "Valladolid": "CL",
    "Zamora": "CL",
    "Zaragoza": "AR",
}

REGION_NAMES = {
    "AN": "Andalucía",
    "AR": "Aragón",
    "AS": "Asturias",
    "CB": "Cantabria",
    "CE": "Ceuta",
    "CL": "Castilla y León",
    "CM": "Castilla-La Mancha",
    "CN": "Canarias",
    "CT": "Cataluña",
    "EX": "Extremadura",
    "GA": "Galicia",
    "IB": "Illes Balears",
    "MC": "Región de Murcia",
    "MD": "Comunidad de Madrid",
    "ML": "Melilla",
    "NC": "Comunidad Foral de Navarra",
    "PV": "País Vasco",
    "RI": "La Rioja",
    "VC": "Comunitat Valenciana",
}

MONTH_CHOICES = [
    ("Enero", 1),
    ("Febrero", 2),
    ("Marzo", 3),
    ("Abril", 4),
    ("Mayo", 5),
    ("Junio", 6),
    ("Julio", 7),
    ("Agosto", 8),
    ("Septiembre", 9),
    ("Octubre", 10),
    ("Noviembre", 11),
    ("Diciembre", 12),
]

MODEL_MODES = [
    ("Comparar modelos", "compare"),
    ("Modelo global", "global"),
    ("Modelo costero ajustado", "coastal"),
    ("Modelo HF Chronos-2", "chronos"),
]

YEAR_CHOICES = [2023, 2024, 2025]

DEMO_PRESETS = {
    "Illes Balears": [8, 27.0, 32.0, 22.8, 18.8, 18.8, 40, 7.8, 15.2, 1, 0, 6_258_000, 49_000, 841_000, 4],
    "Las Palmas": [8, 23.0, 25.9, 21.0, 7.2, 7.2, 38, 13.9, 18.9, 1, 0, 2_369_000, 20_300, 1_573_000, 3],
    "Barcelona": [8, 25.4, 28.8, 21.9, 48.7, 48.7, 69, 9.6, 19.6, 1, 0, 4_944_000, 33_700, 13_188_000, 2],
    "Santa Cruz de Tenerife": [8, 23.0, 26.2, 20.5, 4.7, 4.7, 29, 12.9, 17.3, 1, 0, 1_621_000, 15_000, 1_137_000, 5],
    "Madrid": [10, 15.9, 21.6, 11.0, 59.8, 59.8, 91, 9.0, 15.5, 1, 0, 4_768_000, 37_300, 50_344_000, 2],
    "Malaga": [8, 27.3, 31.4, 23.7, 1.5, 1.5, 11, 8.2, 15.0, 1, 0, 2_119_000, 15_300, 304_000, 1],
    "Alicante": [8, 27.0, 30.0, 24.0, 12.9, 12.9, 25, 11.6, 21.5, 1, 0, 1_562_000, 10_400, 290_000, 1],
    "Girona": [8, 25.1, 31.0, 20.2, 45.2, 45.2, 52, 8.2, 16.7, 1, 0, 289_000, 2_400, 4_000, 1],
    "Tarragona": [8, 25.7, 29.8, 21.8, 47.3, 47.3, 47, 9.0, 18.3, 1, 0, 179_000, 1_700, 0, 1],
    "Cadiz": [8, 25.4, 30.0, 21.2, 0.7, 0.7, 3, 11.5, 18.6, 1, 0, 111_000, 4_900, 0, 2],
}

ARTIFACT_ENV_VARS = {
    GLOBAL_MODEL_FILENAME: "MODEL_PATH",
    GLOBAL_METADATA_FILENAME: "MODEL_METADATA_PATH",
    COASTAL_MODEL_FILENAME: "COASTAL_MODEL_PATH",
    COASTAL_METADATA_FILENAME: "COASTAL_MODEL_METADATA_PATH",
    CHRONOS_CONTEXT_FILENAME: "CHRONOS_CONTEXT_PATH",
}


def resolve_artifact(filename: str) -> str:
    explicit_path = os.getenv(ARTIFACT_ENV_VARS[filename])
    if explicit_path and Path(explicit_path).exists():
        return explicit_path

    for local_path in [
        Path(filename),
        Path("models") / filename,
        Path("..") / "models" / filename,
        Path("..") / ".." / "models" / filename,
    ]:
        if local_path.exists():
            return str(local_path)

    model_repo_id = os.getenv("HF_MODEL_REPO_ID")
    if not model_repo_id:
        raise RuntimeError(
            "HF_MODEL_REPO_ID is not configured. Set it as a Space secret or bundle the model files."
        )
    return hf_hub_download(repo_id=model_repo_id, filename=filename, token=os.getenv("HF_TOKEN"))


GLOBAL_MODEL = joblib.load(resolve_artifact(GLOBAL_MODEL_FILENAME))
COASTAL_MODEL = joblib.load(resolve_artifact(COASTAL_MODEL_FILENAME))

try:
    with open(resolve_artifact(GLOBAL_METADATA_FILENAME), encoding="utf-8") as file:
        GLOBAL_METADATA = json.load(file)
except Exception:
    GLOBAL_METADATA = {}

with open(resolve_artifact(COASTAL_METADATA_FILENAME), encoding="utf-8") as file:
    COASTAL_METADATA = json.load(file)

COASTAL_PROVINCES = set(COASTAL_METADATA["coastal_provinces"])
CHRONOS_PIPELINE = None
CHRONOS_LOAD_ERROR = None
CHRONOS_CONTEXT = None


def load_chronos_context() -> pd.DataFrame:
    global CHRONOS_CONTEXT
    if CHRONOS_CONTEXT is None:
        context = pd.read_csv(resolve_artifact(CHRONOS_CONTEXT_FILENAME))
        context["timestamp"] = pd.to_datetime(context["timestamp"])
        context["target"] = pd.to_numeric(context["target"], errors="coerce")
        CHRONOS_CONTEXT = context.dropna(subset=["target"]).sort_values(["item_id", "timestamp"])
    return CHRONOS_CONTEXT


def load_chronos_pipeline():
    global CHRONOS_PIPELINE, CHRONOS_LOAD_ERROR
    if CHRONOS_PIPELINE is not None:
        return CHRONOS_PIPELINE
    if CHRONOS_LOAD_ERROR is not None:
        return None

    try:
        from chronos import Chronos2Pipeline

        CHRONOS_PIPELINE = Chronos2Pipeline.from_pretrained(
            CHRONOS_MODEL_ID,
            device_map=os.getenv("CHRONOS_DEVICE", "cpu"),
        )
    except Exception as exc:
        CHRONOS_LOAD_ERROR = str(exc)
        return None
    return CHRONOS_PIPELINE


def month_distance(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {str(column).lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    for column in df.columns:
        lowered = str(column).lower()
        if any(candidate in lowered for candidate in candidates):
            return column
    return None


def historical_actual(province: str, target_date: pd.Timestamp) -> float | None:
    context = load_chronos_context()
    row = context[(context["item_id"] == province) & (context["timestamp"] == target_date)]
    if row.empty:
        return None
    return float(row.iloc[0]["target"])


def predict_chronos(province: str, year: int, month: int) -> tuple[float | None, str]:
    try:
        context = load_chronos_context()
    except Exception as exc:
        return None, f"No disponible: no se pudo cargar el contexto Chronos ({exc})."

    target_date = pd.Timestamp(year=int(year), month=int(month), day=1)
    province_context = context[
        (context["item_id"] == province) & (context["timestamp"] < target_date)
    ].copy()
    if len(province_context) < 24:
        return None, "No disponible: Chronos necesita al menos 24 meses históricos previos."

    last_timestamp = province_context["timestamp"].max()
    prediction_length = month_distance(last_timestamp, target_date)
    if prediction_length < 1:
        return None, "No disponible: la fecha debe ser posterior al histórico usado como contexto."
    if prediction_length > 36:
        return None, "No disponible: la demo limita Chronos a 36 meses de horizonte."

    pipeline = load_chronos_pipeline()
    if pipeline is None:
        detail = CHRONOS_LOAD_ERROR or "error desconocido al cargar el modelo"
        return None, f"No disponible: no se pudo cargar {CHRONOS_MODEL_ID} ({detail})."

    try:
        forecast = pipeline.predict_df(
            province_context[["item_id", "timestamp", "target"]],
            prediction_length=prediction_length,
            quantile_levels=[0.1, 0.5, 0.9],
            id_column="item_id",
            timestamp_column="timestamp",
            target="target",
        )
    except Exception as exc:
        return None, f"No disponible: fallo la inferencia Chronos ({exc})."

    forecast["timestamp"] = pd.to_datetime(forecast["timestamp"])
    target_rows = forecast[forecast["timestamp"] == target_date]
    selected = target_rows.iloc[0] if not target_rows.empty else forecast.iloc[-1]
    prediction_column = first_existing_column(forecast, ["0.5", "median", "mean"])
    if prediction_column is None:
        numeric_columns = [
            column
            for column in forecast.select_dtypes(include=[np.number]).columns
            if column not in {"target"}
        ]
        prediction_column = numeric_columns[-1] if numeric_columns else None
    if prediction_column is None:
        return None, "No disponible: Chronos no devolvió una columna numérica interpretable."

    prediction = max(float(selected[prediction_column]), 0.0)
    return prediction, f"Forecast zero-shot con {CHRONOS_MODEL_ID} usando histórico mensual de la provincia."


def build_row(
    province: str,
    month: int,
    temperature_mean: float,
    temperature_max: float,
    temperature_min: float,
    precipitation_sum: float,
    rain_sum: float,
    precipitation_hours: float,
    wind_mean: float,
    wind_max: float,
    national_holidays: int,
    regional_holidays: int,
    aena_passengers: float,
    aena_operations: float,
    aena_cargo_kg: float,
    aena_airport_count: int,
) -> pd.DataFrame:
    region_code = PROVINCE_REGION_CODES[province]
    quarter = int((month - 1) // 3 + 1)
    total_holidays = int(national_holidays + regional_holidays)
    precipitation_sum = max(float(precipitation_sum), 0.0)
    aena_passengers = max(float(aena_passengers), 0.0)
    temperature_bucket = pd.cut(
        pd.Series([temperature_mean]),
        bins=[-np.inf, 10, 18, 25, np.inf],
        labels=["cold", "mild", "warm", "hot"],
    ).astype(str).iloc[0]
    precipitation_bucket = pd.cut(
        pd.Series([precipitation_sum]),
        bins=[-0.001, 20, 80, np.inf],
        labels=["dry", "normal", "rainy"],
    ).astype(str).iloc[0]

    return pd.DataFrame(
        [
            {
                "temperature_2m_mean_avg": float(temperature_mean),
                "temperature_2m_max_avg": float(temperature_max),
                "temperature_2m_min_avg": float(temperature_min),
                "precipitation_sum_total": precipitation_sum,
                "rain_sum_total": max(float(rain_sum), 0.0),
                "precipitation_hours_total": max(float(precipitation_hours), 0.0),
                "wind_speed_10m_mean_avg": max(float(wind_mean), 0.0),
                "wind_speed_10m_max_avg": max(float(wind_max), 0.0),
                "national_holiday_count": int(national_holidays),
                "regional_holiday_count": int(regional_holidays),
                "total_holiday_count": total_holidays,
                "aena_passengers": aena_passengers,
                "aena_operations": max(float(aena_operations), 0.0),
                "aena_cargo_kg": max(float(aena_cargo_kg), 0.0),
                "aena_airport_count": int(aena_airport_count),
                "month": int(month),
                "quarter": quarter,
                "is_high_season": int(month in [6, 7, 8, 9]),
                "aena_passengers_log1p": np.log1p(aena_passengers),
                "precipitation_sqrt": np.sqrt(precipitation_sum),
                "temperature_2m_mean_sq": float(temperature_mean) ** 2,
                "province": province,
                "region_code": region_code,
                "temperature_bucket": temperature_bucket,
                "precipitation_bucket": precipitation_bucket,
            }
        ]
    )


def predict(model_mode: str, history: list[list] | None, *values):
    province = values[0]
    year = int(values[1])
    month = int(values[2])
    row = build_row(province, month, *values[3:])
    month_name = dict((value, label) for label, value in MONTH_CHOICES)[month]
    date_label = f"{month_name} {year}"

    global_prediction = float(np.clip(GLOBAL_MODEL.predict(row)[0], a_min=0, a_max=None))
    coastal_prediction = None
    if province in COASTAL_PROVINCES:
        coastal_prediction = float(np.clip(COASTAL_MODEL.predict(row)[0], a_min=0, a_max=None))
    chronos_prediction, chronos_detail = predict_chronos(province, year, month)

    if model_mode == "coastal" and coastal_prediction is None:
        prediction = global_prediction
        interpretation = (
            "El modelo costero no es aplicable a esta provincia. "
            "Se devuelve el modelo global."
        )
    elif model_mode == "coastal":
        prediction = coastal_prediction
        interpretation = "Resultado mostrado: modelo costero ajustado."
    elif model_mode == "global":
        prediction = global_prediction
        interpretation = "Resultado mostrado: modelo global."
    elif model_mode == "chronos" and chronos_prediction is not None:
        prediction = chronos_prediction
        interpretation = f"Resultado mostrado: modelo HF Chronos-2. {chronos_detail}"
    elif model_mode == "chronos":
        prediction = global_prediction
        interpretation = f"Chronos-2 no está disponible para esta entrada. {chronos_detail} Se devuelve el modelo global."
    elif coastal_prediction is None:
        prediction = global_prediction
        interpretation = "Solo está disponible el modelo global para esta provincia."
    else:
        prediction = global_prediction
        interpretation = ""

    coastal_display = (
        f"{coastal_prediction:,.0f}" if coastal_prediction is not None else "No aplicable"
    )
    difference_display = (
        f"{coastal_prediction - global_prediction:+,.0f}"
        if coastal_prediction is not None
        else "No aplicable"
    )
    difference_percent = (
        (coastal_prediction - global_prediction) / global_prediction * 100
        if coastal_prediction is not None and global_prediction
        else None
    )
    difference_percent_display = (
        f"{difference_percent:+.1f}%" if difference_percent is not None else "No aplicable"
    )
    chronos_display = (
        f"{chronos_prediction:,.0f}" if chronos_prediction is not None else "No disponible"
    )
    if model_mode == "compare" and coastal_prediction is not None:
        prediction = global_prediction
        interpretation = (
            "Comparación informativa; el modelo global se conserva como referencia. "
            f"El modelo costero difiere en {difference_display} ({difference_percent_display})."
        )
        if abs(difference_percent) >= 20:
            interpretation += (
                " La divergencia es alta: revisa que los valores formen una combinación "
                "realista antes de interpretar la predicción."
            )
        if chronos_prediction is not None:
            interpretation += f" Chronos-2 aporta una referencia HF de {chronos_display}."
        else:
            interpretation += f" {chronos_detail}"
    elif model_mode == "compare" and chronos_prediction is not None:
        interpretation += f" Chronos-2 aporta una referencia HF de {chronos_display}."
    elif model_mode == "compare":
        interpretation += f" {chronos_detail}"

    target_date = pd.Timestamp(year=year, month=month, day=1)
    actual_value = historical_actual(province, target_date)
    actual_display = f"{actual_value:,.0f}" if actual_value is not None else "No disponible"
    new_history_row = [
        province,
        region_for_province(province),
        date_label,
        f"{global_prediction:,.0f}",
        coastal_display,
        chronos_display,
        difference_display,
    ]
    updated_history = [new_history_row, *(history or [])][:5]
    comparison = {
        "Modelo global": round(global_prediction),
        "Modelo costero ajustado": round(coastal_prediction) if coastal_prediction is not None else "No aplicable",
        "Modelo HF Chronos-2": round(chronos_prediction) if chronos_prediction is not None else "No disponible",
        "Real histórico": actual_display,
        "Diferencia costero - global": difference_display,
        "Diferencia porcentual": difference_percent_display,
        "Segmento": "Costero/insular" if province in COASTAL_PROVINCES else "Resto de provincias",
        "Detalle Chronos-2": chronos_detail,
    }
    return (
        round(prediction),
        comparison,
        interpretation,
        row,
        render_history(updated_history),
        updated_history,
    )


def region_for_province(province: str) -> str:
    if not province:
        return ""
    region_code = PROVINCE_REGION_CODES[province]
    return f"{REGION_NAMES[region_code]} ({region_code})"


def segment_status(province: str) -> str:
    if province in COASTAL_PROVINCES:
        return (
            "Provincia incluida en el segmento costero/insular. "
            "Se pueden comparar ambos modelos."
        )
    return (
        "Provincia fuera del segmento costero/insular. "
        "El modelo especializado no es aplicable."
    )


def apply_province_preset(province: str):
    status = segment_status(province)
    preset = DEMO_PRESETS.get(province)
    if preset is None:
        return region_for_province(province), status, *([gr.skip()] * 15)
    status += (
        " Se ha cargado su preset demostrativo, basado en las medianas históricas "
        "del mes con mayor demanda turística media."
    )
    return region_for_province(province), status, *preset


def render_history(history: list[list] | None) -> str:
    rows = history or []
    if not rows:
        return "<p>Todavía no hay predicciones en esta sesión.</p>"

    header = "".join(f"<th>{escape(column)}</th>" for column in HISTORY_COLUMNS)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows[:5]
    )
    return (
        '<div style="overflow-x:auto">'
        '<table style="width:100%; border-collapse:collapse">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table></div>"
        "<style>"
        "table th, table td {padding: 8px; border-bottom: 1px solid #ddd; text-align: left;}"
        "table th {font-weight: 600;}"
        "</style>"
    )


with gr.Blocks(title="Tourism Weather ML") as demo:
    gr.Markdown("# Tourism Weather ML")
    gr.Markdown(
        "Estimación de pernoctaciones hoteleras mensuales por provincia. "
        "Permite comparar el modelo global con el modelo ajustado para provincias "
        "costeras e insulares y una referencia HF basada en Chronos-2."
    )
    gr.Markdown(
        "**Demostración rápida:** Illes Balears, Las Palmas, Barcelona, Santa Cruz de "
        "Tenerife, Madrid, Málaga, Alicante, Girona, Tarragona y Cádiz tienen valores "
        "iniciales coherentes con su histórico. Al seleccionar una de ellas se carga "
        "automáticamente el escenario mediano de su mes con mayor demanda turística."
    )
    prediction_history = gr.State([])

    with gr.Accordion("Modelo, territorio y fecha", open=True):
        model_mode = gr.Radio(choices=MODEL_MODES, value="compare", label="Modo de predicción")
        with gr.Row():
            province = gr.Dropdown(
                choices=sorted(PROVINCE_REGION_CODES),
                value="Malaga",
                label="Provincia",
            )
            region_code = gr.Textbox(
                value="Andalucía (AN)",
                label="Comunidad autónoma",
                interactive=False,
                info="El código autonómico usado por el modelo se completa automáticamente.",
            )
            year = gr.Dropdown(choices=YEAR_CHOICES, value=2024, label="Año para Chronos-2")
            month = gr.Dropdown(choices=MONTH_CHOICES, value=8, label="Mes")
        segment = gr.Markdown(segment_status("Malaga"))

    with gr.Accordion("Clima mensual", open=True):
        with gr.Row():
            temperature_mean = gr.Slider(
                0, 32, value=27.3, step=0.1, label="Temperatura media (°C)"
            )
            temperature_max = gr.Slider(
                4, 41, value=31.4, step=0.1, label="Temperatura máxima media (°C)"
            )
            temperature_min = gr.Slider(
                -3, 26, value=23.7, step=0.1, label="Temperatura mínima media (°C)"
            )
        with gr.Row():
            precipitation_sum = gr.Slider(
                0, 470, value=1.5, step=0.1, label="Precipitación total (mm)"
            )
            rain_sum = gr.Slider(0, 470, value=1.5, step=0.1, label="Lluvia total (mm)")
            precipitation_hours = gr.Slider(
                0, 490, value=11, step=1, label="Horas de precipitación"
            )
        with gr.Row():
            wind_mean = gr.Slider(
                4, 28, value=8.2, step=0.1, label="Velocidad media del viento (km/h)"
            )
            wind_max = gr.Slider(
                7, 38, value=15, step=0.1, label="Velocidad máxima media (km/h)"
            )

    with gr.Accordion("Calendario y movilidad aeroportuaria", open=False):
        with gr.Row():
            national_holidays = gr.Dropdown(
                choices=[0, 1, 2, 3], value=1, label="Festivos nacionales"
            )
            regional_holidays = gr.Dropdown(
                choices=[0, 1, 2, 3], value=0, label="Festivos regionales"
            )
            aena_airport_count = gr.Dropdown(
                choices=[0, 1, 2, 3, 4, 5], value=1, label="Aeropuertos AENA"
            )
        with gr.Row():
            aena_passengers = gr.Slider(
                0, 7_000_000, value=2_119_000, step=1_000, label="Pasajeros AENA"
            )
            aena_operations = gr.Slider(
                0, 52_000, value=15_300, step=100, label="Operaciones AENA"
            )
            aena_cargo_kg = gr.Slider(
                0, 73_000_000, value=304_000, step=1_000, label="Carga AENA (kg)"
            )

    province.change(
        apply_province_preset,
        inputs=province,
        outputs=[
            region_code,
            segment,
            month,
            temperature_mean,
            temperature_max,
            temperature_min,
            precipitation_sum,
            rain_sum,
            precipitation_hours,
            wind_mean,
            wind_max,
            national_holidays,
            regional_holidays,
            aena_passengers,
            aena_operations,
            aena_cargo_kg,
            aena_airport_count,
        ],
    )

    button = gr.Button("Calcular y comparar", variant="primary")
    with gr.Row():
        prediction = gr.Number(label="Pernoctaciones hoteleras estimadas", precision=0)
        comparison = gr.JSON(label="Comparación de modelos")
    interpretation = gr.Textbox(label="Interpretación", interactive=False)
    with gr.Accordion("Detalle de las variables enviadas al modelo", open=False):
        row_preview = gr.Dataframe(label="Features calculadas", interactive=False)
    gr.Markdown("## Últimas predicciones")
    history_table = gr.HTML(value=render_history([]), label="Historial de esta sesión")

    button.click(
        predict,
        inputs=[
            model_mode,
            prediction_history,
            province,
            year,
            month,
            temperature_mean,
            temperature_max,
            temperature_min,
            precipitation_sum,
            rain_sum,
            precipitation_hours,
            wind_mean,
            wind_max,
            national_holidays,
            regional_holidays,
            aena_passengers,
            aena_operations,
            aena_cargo_kg,
            aena_airport_count,
        ],
        outputs=[
            prediction,
            comparison,
            interpretation,
            row_preview,
            history_table,
            prediction_history,
        ],
    )


if __name__ == "__main__":
    demo.launch()
