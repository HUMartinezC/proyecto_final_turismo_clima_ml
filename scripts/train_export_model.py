#!/usr/bin/env python3
"""Train and export the selected tourism-demand model."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "datasets" / "processed" / "gold" / "tourism_weather_monthly_features.csv"
DEFAULT_MODELS_DIR = ROOT / "models"
DEFAULT_FIGURES_DIR = ROOT / "reports" / "figures"

TARGET = "hotel_overnights"
CHRONOS_CONTEXT_FILENAME = "chronos_context.csv"

NUMERIC_FEATURES = [
    "temperature_2m_mean_avg",
    "temperature_2m_max_avg",
    "temperature_2m_min_avg",
    "precipitation_sum_total",
    "rain_sum_total",
    "precipitation_hours_total",
    "wind_speed_10m_mean_avg",
    "wind_speed_10m_max_avg",
    "national_holiday_count",
    "regional_holiday_count",
    "total_holiday_count",
    "aena_passengers",
    "aena_operations",
    "aena_cargo_kg",
    "aena_airport_count",
    "month",
    "quarter",
    "is_high_season",
    "aena_passengers_log1p",
    "temperature_2m_mean_sq",
    "precipitation_sqrt",
]

CATEGORICAL_FEATURES = [
    "province",
    "region_code",
    "temperature_bucket",
    "precipitation_bucket",
]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["date"] = pd.to_datetime(result["year_month"] + "-01")
    result["year"] = result["date"].dt.year
    result["month"] = result["date"].dt.month
    result["quarter"] = result["date"].dt.quarter
    result["is_high_season"] = result["month"].isin([6, 7, 8, 9]).astype(int)
    result["aena_passengers_log1p"] = np.log1p(result["aena_passengers"].clip(lower=0))
    result["precipitation_sqrt"] = np.sqrt(result["precipitation_sum_total"].clip(lower=0))
    result["temperature_2m_mean_sq"] = result["temperature_2m_mean_avg"] ** 2
    result["temperature_bucket"] = pd.cut(
        result["temperature_2m_mean_avg"],
        bins=[-np.inf, 10, 18, 25, np.inf],
        labels=["cold", "mild", "warm", "hot"],
    )
    result["precipitation_bucket"] = pd.cut(
        result["precipitation_sum_total"],
        bins=[-0.001, 20, 80, np.inf],
        labels=["dry", "normal", "rainy"],
    )
    return result


def temporal_split(df: pd.DataFrame, train_ratio: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    months = sorted(df["year_month"].unique())
    split_index = int(len(months) * train_ratio)
    train_months = set(months[:split_index])
    train_df = df[df["year_month"].isin(train_months)].copy()
    test_df = df[~df["year_month"].isin(train_months)].copy()
    return train_df, test_df


def save_chronos_context(df: pd.DataFrame, output_path: Path) -> None:
    context = (
        df[["province", "year_month", TARGET]]
        .dropna(subset=[TARGET])
        .rename(
            columns={
                "province": "item_id",
                "year_month": "timestamp",
                TARGET: "target",
            }
        )
        .sort_values(["item_id", "timestamp"])
    )
    context["timestamp"] = context["timestamp"] + "-01"
    context.to_csv(output_path, index=False)


def build_pipeline() -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
            ("categorical", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )
    model = ExtraTreesRegressor(
        n_estimators=180,
        max_depth=None,
        min_samples_leaf=1,
        min_samples_split=5,
        max_features=1.0,
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def save_figures(
    predictions: pd.DataFrame,
    pipeline: Pipeline,
    figures_dir: Path,
) -> pd.DataFrame:
    figures_dir.mkdir(parents=True, exist_ok=True)

    y_true = predictions["y_true"]
    y_pred = predictions["y_pred"]
    residuals = y_true - y_pred

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(y_true, y_pred, alpha=0.45, s=18)
    limit = max(float(y_true.max()), float(y_pred.max()))
    ax.plot([0, limit], [0, limit], color="black", linestyle="--", linewidth=1)
    ax.set_title("Predicciones vs valores reales")
    ax.set_xlabel("Pernoctaciones reales")
    ax.set_ylabel("Pernoctaciones predichas")
    fig.tight_layout()
    fig.savefig(figures_dir / "predictions_vs_actual.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(y_pred, residuals, alpha=0.45, s=18)
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Residuos del mejor modelo")
    ax.set_xlabel("Prediccion")
    ax.set_ylabel("Real - predicho")
    fig.tight_layout()
    fig.savefig(figures_dir / "residuals.png", dpi=160)
    plt.close(fig)

    monthly = predictions.groupby("year_month", as_index=False)[["y_true", "y_pred"]].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly["year_month"], monthly["y_true"], label="Real", marker="o", linewidth=1.5)
    ax.plot(monthly["year_month"], monthly["y_pred"], label="Prediccion", marker="o", linewidth=1.5)
    ax.set_title("Demanda real vs predicha por mes")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Pernoctaciones")
    ax.tick_params(axis="x", rotation=60)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "monthly_actual_vs_predicted.png", dpi=160)
    plt.close(fig)

    model = pipeline.named_steps["model"]
    feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importances = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    top_importances = importances.head(20).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top_importances["feature"], top_importances["importance"])
    ax.set_title("Top 20 variables por importancia")
    ax.set_xlabel("Importancia")
    fig.tight_layout()
    fig.savefig(figures_dir / "feature_importance.png", dpi=160)
    plt.close(fig)

    return importances


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and export the selected tourism-weather model.")
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    args = parser.parse_args()

    df = pd.read_csv(args.gold_path)
    df = add_features(df)
    df = df.dropna(subset=[TARGET]).sort_values(["date", "province"]).reset_index(drop=True)

    train_df, test_df = temporal_split(df)
    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    x_train = train_df[feature_columns]
    y_train = train_df[TARGET]
    x_test = test_df[feature_columns]
    y_test = test_df[TARGET]

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)
    y_pred = np.clip(pipeline.predict(x_test), a_min=0, a_max=None)

    metrics = {
        "model_name": "ExtraTrees optimizado",
        "selection_source": "notebooks/proyecto_final_turismo_clima_cloud.ipynb",
        "model_params": pipeline.named_steps["model"].get_params(),
        "target": TARGET,
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_month_min": str(train_df["year_month"].min()),
        "train_month_max": str(train_df["year_month"].max()),
        "test_month_min": str(test_df["year_month"].min()),
        "test_month_max": str(test_df["year_month"].max()),
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }

    predictions = pd.DataFrame(
        {
            "province": test_df["province"].values,
            "year_month": test_df["year_month"].values,
            "y_true": y_test.values,
            "y_pred": y_pred,
            "absolute_error": np.abs(y_test.values - y_pred),
        }
    )
    importances = save_figures(predictions, pipeline, args.figures_dir)

    args.models_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.models_dir / "tourism_weather_extra_trees.joblib"
    metadata_path = args.models_dir / "model_metadata.json"
    sample_path = args.models_dir / "sample_input.json"

    joblib.dump(pipeline, model_path)
    metadata_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    sample_path.write_text(
        json.dumps(x_test.iloc[0].to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    predictions.to_csv(args.models_dir / "test_predictions.csv", index=False)
    importances.to_csv(args.models_dir / "feature_importance.csv", index=False)
    save_chronos_context(df, args.models_dir / CHRONOS_CONTEXT_FILENAME)

    print(f"Model saved to {model_path}")
    print(f"Metadata saved to {metadata_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
