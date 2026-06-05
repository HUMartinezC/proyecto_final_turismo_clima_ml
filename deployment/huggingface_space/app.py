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


MODEL_FILENAME = "tourism_weather_extra_trees.joblib"
METADATA_FILENAME = "model_metadata.json"
HISTORY_COLUMNS = [
    "Provincia",
    "Comunidad autónoma",
    "Mes",
    "Temperatura media (°C)",
    "Precipitación total (mm)",
    "Pasajeros AENA",
    "Predicción de pernoctaciones",
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


def resolve_artifact(filename: str) -> str:
    explicit_path = os.getenv("MODEL_PATH" if filename.endswith(".joblib") else "MODEL_METADATA_PATH")
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


MODEL = joblib.load(resolve_artifact(MODEL_FILENAME))

try:
    with open(resolve_artifact(METADATA_FILENAME), encoding="utf-8") as file:
        METADATA = json.load(file)
except Exception:
    METADATA = {}


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


def predict(history: list[list] | None, *values):
    row = build_row(*values)
    prediction = float(np.clip(MODEL.predict(row)[0], a_min=0, a_max=None))
    metrics = ""
    if METADATA:
        metrics = (
            f"Modelo: {METADATA.get('model_name', 'ExtraTreesRegressor')} | "
            f"RMSE test: {METADATA.get('RMSE', 0):,.0f} | "
            f"MAE test: {METADATA.get('MAE', 0):,.0f} | "
            f"R2 test: {METADATA.get('R2', 0):.3f}"
        )
    province = values[0]
    month = int(values[1])
    temperature_mean = float(values[2])
    precipitation_sum = float(values[5])
    aena_passengers = int(values[12])
    month_name = dict((value, label) for label, value in MONTH_CHOICES)[month]
    new_history_row = [
        province,
        region_for_province(province),
        month_name,
        round(temperature_mean, 1),
        round(precipitation_sum, 1),
        aena_passengers,
        round(prediction),
    ]
    updated_history = [new_history_row, *(history or [])][:5]
    return round(prediction), metrics, row, render_history(updated_history), updated_history


def region_for_province(province: str) -> str:
    if not province:
        return ""
    region_code = PROVINCE_REGION_CODES[province]
    return f"{REGION_NAMES[region_code]} ({region_code})"


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
        "Los rangos de los controles se basan en los datos históricos del proyecto."
    )
    prediction_history = gr.State([])

    with gr.Accordion("Territorio y fecha", open=True):
        with gr.Row():
            province = gr.Dropdown(
                choices=sorted(PROVINCE_REGION_CODES),
                value="A Coruna",
                label="Provincia",
            )
            region_code = gr.Textbox(
                value="Galicia (GA)",
                label="Comunidad autónoma",
                interactive=False,
                info="El código autonómico usado por el modelo se completa automáticamente.",
            )
            month = gr.Dropdown(choices=MONTH_CHOICES, value=8, label="Mes")

    with gr.Accordion("Clima mensual", open=True):
        with gr.Row():
            temperature_mean = gr.Slider(
                0, 32, value=21, step=0.1, label="Temperatura media (°C)"
            )
            temperature_max = gr.Slider(
                4, 41, value=26, step=0.1, label="Temperatura máxima media (°C)"
            )
            temperature_min = gr.Slider(
                -3, 26, value=16, step=0.1, label="Temperatura mínima media (°C)"
            )
        with gr.Row():
            precipitation_sum = gr.Slider(
                0, 470, value=35, step=1, label="Precipitación total (mm)"
            )
            rain_sum = gr.Slider(0, 470, value=35, step=1, label="Lluvia total (mm)")
            precipitation_hours = gr.Slider(
                0, 490, value=45, step=1, label="Horas de precipitación"
            )
        with gr.Row():
            wind_mean = gr.Slider(
                4, 28, value=12, step=0.1, label="Velocidad media del viento (km/h)"
            )
            wind_max = gr.Slider(
                7, 38, value=22, step=0.1, label="Velocidad máxima media (km/h)"
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
                0, 7_000_000, value=300_000, step=10_000, label="Pasajeros AENA"
            )
            aena_operations = gr.Slider(
                0, 52_000, value=3_000, step=100, label="Operaciones AENA"
            )
            aena_cargo_kg = gr.Slider(
                0, 73_000_000, value=200_000, step=100_000, label="Carga AENA (kg)"
            )

    province.change(region_for_province, inputs=province, outputs=region_code)

    button = gr.Button("Calcular predicción", variant="primary")
    with gr.Row():
        prediction = gr.Number(label="Pernoctaciones hoteleras estimadas", precision=0)
        metrics = gr.Textbox(label="Métricas del modelo", interactive=False)
    with gr.Accordion("Detalle de las variables enviadas al modelo", open=False):
        row_preview = gr.Dataframe(label="Features calculadas", interactive=False)
    gr.Markdown("## Últimas predicciones")
    history_table = gr.HTML(value=render_history([]), label="Historial de esta sesión")

    button.click(
        predict,
        inputs=[
            prediction_history,
            province,
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
        outputs=[prediction, metrics, row_preview, history_table, prediction_history],
    )


if __name__ == "__main__":
    demo.launch()
