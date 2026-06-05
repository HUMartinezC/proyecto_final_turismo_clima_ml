#!/usr/bin/env python3
"""Fine-tune and evaluate a model specialized in coastal and island provinces."""

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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import PredefinedSplit, RandomizedSearchCV

from train_export_model import (
    CATEGORICAL_FEATURES,
    DEFAULT_GOLD,
    DEFAULT_MODELS_DIR,
    NUMERIC_FEATURES,
    TARGET,
    add_features,
    build_pipeline,
    temporal_split,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "fine_tuning"
DEFAULT_FIGURES_DIR = ROOT / "reports" / "figures"

# Provinces whose territory has a sea coast, including autonomous island/city territories.
COASTAL_PROVINCES = [
    "A Coruna",
    "Alicante",
    "Almeria",
    "Asturias",
    "Barcelona",
    "Bizkaia",
    "Cadiz",
    "Cantabria",
    "Castellon",
    "Ceuta",
    "Gipuzkoa",
    "Girona",
    "Granada",
    "Huelva",
    "Illes Balears",
    "Las Palmas",
    "Lugo",
    "Malaga",
    "Melilla",
    "Murcia",
    "Pontevedra",
    "Santa Cruz de Tenerife",
    "Tarragona",
    "Valencia",
]

PARAMETER_DISTRIBUTIONS = {
    "model__n_estimators": [180, 260, 360, 500],
    "model__max_depth": [8, 10, 12, 16, None],
    "model__min_samples_leaf": [1, 2, 4, 8],
    "model__min_samples_split": [2, 5, 10],
    "model__max_features": ["sqrt", 0.7, 1.0],
    "model__bootstrap": [False, True],
}


def metrics_for(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def improvement_percent(baseline: float, candidate: float, higher_is_better: bool = False) -> float:
    if higher_is_better:
        return float((candidate - baseline) / abs(baseline) * 100)
    return float((baseline - candidate) / baseline * 100)


def make_temporal_validation_split(df: pd.DataFrame, train_ratio: float = 0.8) -> PredefinedSplit:
    months = sorted(df["year_month"].unique())
    split_index = int(len(months) * train_ratio)
    validation_months = set(months[split_index:])
    test_fold = np.where(df["year_month"].isin(validation_months), 0, -1)
    return PredefinedSplit(test_fold)


def save_figures(predictions: pd.DataFrame, metrics: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    colors = ["#777777", "#4c78a8", "#f58518"]
    for ax, metric in zip(axes, ["MAE", "RMSE"]):
        ax.bar(metrics["model"], metrics[metric], color=colors)
        ax.set_title(f"{metric} en provincias costeras e insulares")
        ax.set_ylabel(metric)
        ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(figures_dir / "coastal_model_metrics.png", dpi=160)
    plt.close(fig)

    monthly = (
        predictions.groupby("year_month", as_index=False)[
            ["y_true", "global_prediction", "tuned_coastal_prediction"]
        ]
        .sum()
        .sort_values("year_month")
    )
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(monthly["year_month"], monthly["y_true"], label="Real", marker="o")
    ax.plot(monthly["year_month"], monthly["global_prediction"], label="Modelo global", marker="o")
    ax.plot(
        monthly["year_month"],
        monthly["tuned_coastal_prediction"],
        label="Modelo costero ajustado",
        marker="o",
    )
    ax.set_title("Demanda costera e insular agregada: real vs prediccion")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Pernoctaciones")
    ax.tick_params(axis="x", rotation=60)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "coastal_monthly_predictions.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--n-iter", type=int, default=24)
    args = parser.parse_args()

    df = add_features(pd.read_csv(args.gold_path))
    df = df.dropna(subset=[TARGET]).sort_values(["date", "province"]).reset_index(drop=True)
    global_train, global_test = temporal_split(df)

    coastal_train = global_train[global_train["province"].isin(COASTAL_PROVINCES)].copy()
    coastal_test = global_test[global_test["province"].isin(COASTAL_PROVINCES)].copy()
    missing_provinces = sorted(set(COASTAL_PROVINCES) - set(df["province"].unique()))
    if missing_provinces:
        raise ValueError(f"Coastal provinces missing from gold dataset: {missing_provinces}")
    if coastal_train.empty or coastal_test.empty:
        raise ValueError("The coastal train/test segment is empty.")

    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    x_global_train = global_train[feature_columns]
    y_global_train = global_train[TARGET]
    x_coastal_train = coastal_train[feature_columns]
    y_coastal_train = coastal_train[TARGET]
    x_coastal_test = coastal_test[feature_columns]
    y_coastal_test = coastal_test[TARGET]

    global_pipeline = build_pipeline()
    global_pipeline.fit(x_global_train, y_global_train)
    global_prediction = np.clip(global_pipeline.predict(x_coastal_test), 0, None)

    default_coastal_pipeline = build_pipeline()
    default_coastal_pipeline.fit(x_coastal_train, y_coastal_train)
    default_coastal_prediction = np.clip(default_coastal_pipeline.predict(x_coastal_test), 0, None)

    search = RandomizedSearchCV(
        estimator=build_pipeline(),
        param_distributions=PARAMETER_DISTRIBUTIONS,
        n_iter=args.n_iter,
        scoring="neg_root_mean_squared_error",
        cv=make_temporal_validation_split(coastal_train),
        refit=True,
        random_state=42,
        n_jobs=1,
        verbose=1,
        return_train_score=True,
    )
    search.fit(x_coastal_train, y_coastal_train)
    tuned_coastal_pipeline = search.best_estimator_
    tuned_coastal_prediction = np.clip(tuned_coastal_pipeline.predict(x_coastal_test), 0, None)

    metric_rows = []
    for model_name, prediction in [
        ("Global ExtraTrees", global_prediction),
        ("Coastal ExtraTrees", default_coastal_prediction),
        ("Tuned coastal ExtraTrees", tuned_coastal_prediction),
    ]:
        metric_rows.append({"model": model_name, **metrics_for(y_coastal_test, prediction)})
    metrics = pd.DataFrame(metric_rows)

    global_metrics = metric_rows[0]
    tuned_metrics = metric_rows[2]
    improvements = {
        "MAE_percent": improvement_percent(global_metrics["MAE"], tuned_metrics["MAE"]),
        "RMSE_percent": improvement_percent(global_metrics["RMSE"], tuned_metrics["RMSE"]),
        "R2_percent": improvement_percent(global_metrics["R2"], tuned_metrics["R2"], higher_is_better=True),
    }

    predictions = pd.DataFrame(
        {
            "province": coastal_test["province"].values,
            "year_month": coastal_test["year_month"].values,
            "y_true": y_coastal_test.values,
            "global_prediction": global_prediction,
            "default_coastal_prediction": default_coastal_prediction,
            "tuned_coastal_prediction": tuned_coastal_prediction,
        }
    )
    for prediction_column in [
        "global_prediction",
        "default_coastal_prediction",
        "tuned_coastal_prediction",
    ]:
        predictions[f"{prediction_column}_absolute_error"] = np.abs(
            predictions["y_true"] - predictions[prediction_column]
        )

    province_comparison = (
        predictions.groupby("province", as_index=False)
        .agg(
            global_MAE=("global_prediction_absolute_error", "mean"),
            default_coastal_MAE=("default_coastal_prediction_absolute_error", "mean"),
            tuned_coastal_MAE=("tuned_coastal_prediction_absolute_error", "mean"),
        )
        .sort_values("province")
    )
    province_comparison["tuned_vs_global_MAE_improvement_percent"] = (
        (province_comparison["global_MAE"] - province_comparison["tuned_coastal_MAE"])
        / province_comparison["global_MAE"]
        * 100
    )

    validation_months = coastal_train.loc[
        make_temporal_validation_split(coastal_train).test_fold == 0, "year_month"
    ]
    metadata = {
        "specialization": "Spanish coastal and island provinces",
        "source": "scripts/fine_tune_coastal_model.py",
        "target": TARGET,
        "coastal_provinces": COASTAL_PROVINCES,
        "coastal_province_count": len(COASTAL_PROVINCES),
        "global_train_rows": len(global_train),
        "coastal_train_rows": len(coastal_train),
        "coastal_test_rows": len(coastal_test),
        "train_month_min": str(coastal_train["year_month"].min()),
        "train_month_max": str(coastal_train["year_month"].max()),
        "validation_month_min": str(validation_months.min()),
        "validation_month_max": str(validation_months.max()),
        "test_month_min": str(coastal_test["year_month"].min()),
        "test_month_max": str(coastal_test["year_month"].max()),
        "search_iterations": args.n_iter,
        "search_best_validation_RMSE": float(-search.best_score_),
        "search_best_params": search.best_params_,
        "metrics": {row["model"]: {key: row[key] for key in ["MAE", "RMSE", "R2"]} for row in metric_rows},
        "tuned_vs_global_improvement": improvements,
        "provinces_with_MAE_improvement": int(
            (province_comparison["tuned_vs_global_MAE_improvement_percent"] > 0).sum()
        ),
    }

    args.models_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(tuned_coastal_pipeline, args.models_dir / "tourism_weather_coastal_extra_trees.joblib")
    (args.models_dir / "coastal_model_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    predictions.to_csv(args.models_dir / "coastal_test_predictions.csv", index=False)
    metrics.to_csv(args.report_dir / "coastal_model_comparison.csv", index=False)
    province_comparison.to_csv(args.report_dir / "coastal_province_comparison.csv", index=False)
    pd.DataFrame(search.cv_results_).to_csv(args.report_dir / "coastal_hyperparameter_search.csv", index=False)
    (args.report_dir / "coastal_model_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    save_figures(predictions, metrics, args.figures_dir)

    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
