#!/usr/bin/env python3
"""Upload the trained model and Gradio Space to Hugging Face Hub."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from huggingface_hub import HfApi, upload_folder


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "models"
DEFAULT_SPACE_DIR = ROOT / "deployment" / "huggingface_space"
STALE_SPACE_ARTIFACTS = [
    "tourism_weather_extra_trees.joblib",
    "tourism_weather_coastal_extra_trees.joblib",
    "model_metadata.json",
    "coastal_model_metadata.json",
    "coastal_test_predictions.csv",
    "chronos_context.csv",
    "province_month_presets.csv",
    "sample_input.json",
    "feature_importance.csv",
    "test_predictions.csv",
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_env_file(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Deploy the tourism-weather model to Hugging Face.")
    parser.add_argument("--model-repo-id", default=os.getenv("HF_MODEL_REPO_ID"))
    parser.add_argument("--space-repo-id", default=os.getenv("HF_SPACE_REPO_ID"))
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--space-dir", type=Path, default=DEFAULT_SPACE_DIR)
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=600,
        help="Wait for the Space build and report READY/RUNNING or BUILD_ERROR.",
    )
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("HF_TOKEN is required. Set it in the environment or pass --token.")
    api = HfApi(token=args.token)
    username = api.whoami().get("name")
    if not username:
        raise SystemExit("Could not determine the Hugging Face username from HF_TOKEN.")
    args.model_repo_id = args.model_repo_id or f"{username}/tourism-weather-model"
    args.space_repo_id = args.space_repo_id or f"{username}/tourism-weather-demo"
    if not args.model_repo_id:
        raise SystemExit("HF_MODEL_REPO_ID is required, for example user/tourism-weather-model.")
    if not args.space_repo_id:
        raise SystemExit("HF_SPACE_REPO_ID is required, for example user/tourism-weather-demo.")

    model_file = args.model_dir / "tourism_weather_extra_trees.joblib"
    metadata_file = args.model_dir / "model_metadata.json"
    sample_file = args.model_dir / "sample_input.json"
    coastal_model_file = args.model_dir / "tourism_weather_coastal_extra_trees.joblib"
    coastal_metadata_file = args.model_dir / "coastal_model_metadata.json"
    chronos_context_file = args.model_dir / "chronos_context.csv"
    province_month_presets_file = args.model_dir / "province_month_presets.csv"
    for path in (
        model_file,
        metadata_file,
        sample_file,
        coastal_model_file,
        coastal_metadata_file,
        chronos_context_file,
        province_month_presets_file,
    ):
        if not path.exists():
            raise SystemExit(
                f"Missing {path}. Run scripts/train_export_model.py and "
                "scripts/fine_tune_coastal_model.py first."
            )

    print(f"Authenticated as {username}")
    print(f"Model repository: {args.model_repo_id}")
    print(f"Space repository: {args.space_repo_id}")

    api.create_repo(args.model_repo_id, repo_type="model", private=args.private, exist_ok=True)
    api.create_repo(args.space_repo_id, repo_type="space", space_sdk="gradio", private=args.private, exist_ok=True)

    print("Uploading model artifacts...")
    upload_folder(
        repo_id=args.model_repo_id,
        repo_type="model",
        folder_path=str(args.model_dir),
        allow_patterns=["*.joblib", "*.json", "*.csv"],
        token=args.token,
    )

    space_info = api.space_info(args.space_repo_id, files_metadata=False)
    existing_files = {sibling.rfilename for sibling in space_info.siblings}
    stale_files = [path for path in STALE_SPACE_ARTIFACTS if path in existing_files]
    if stale_files:
        print(f"Removing stale model artifacts from Space: {', '.join(stale_files)}")
        api.delete_files(
            repo_id=args.space_repo_id,
            repo_type="space",
            delete_patterns=stale_files,
            commit_message="Remove model artifacts from Space repository",
            token=args.token,
        )

    print("Uploading Gradio Space files...")
    upload_folder(
        repo_id=args.space_repo_id,
        repo_type="space",
        folder_path=str(args.space_dir),
        allow_patterns=["app.py", "README.md", "requirements.txt"],
        token=args.token,
    )

    api.add_space_variable(
        args.space_repo_id,
        "HF_MODEL_REPO_ID",
        args.model_repo_id,
        description="Repository containing the exported scikit-learn model.",
        token=args.token,
    )
    if args.private:
        api.add_space_secret(args.space_repo_id, "HF_TOKEN", args.token, token=args.token)

    api.restart_space(args.space_repo_id, token=args.token, factory_reboot=True)
    print(f"Model repo: https://huggingface.co/{args.model_repo_id}")
    print(f"Space: https://huggingface.co/spaces/{args.space_repo_id}")

    deadline = time.monotonic() + args.wait_seconds
    last_stage = None
    while time.monotonic() < deadline:
        runtime = api.get_space_runtime(args.space_repo_id, token=args.token)
        stage = runtime.stage
        if stage != last_stage:
            print(f"Space stage: {stage}")
            last_stage = stage
        if stage in {"RUNNING", "READY", "SLEEPING"}:
            return
        if stage in {"BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"}:
            error_message = runtime.raw.get("errorMessage", "No error message returned.")
            raise SystemExit(f"Space failed with stage {stage}: {error_message}")
        time.sleep(10)
    raise SystemExit(f"Timed out waiting {args.wait_seconds}s for Space build.")


if __name__ == "__main__":
    main()
