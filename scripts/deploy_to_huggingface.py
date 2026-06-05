#!/usr/bin/env python3
"""Upload the trained model and Gradio Space to Hugging Face Hub."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi, upload_folder


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "models"
DEFAULT_SPACE_DIR = ROOT / "deployment" / "huggingface_space"


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
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("HF_TOKEN is required. Set it in the environment or pass --token.")
    if not args.model_repo_id:
        raise SystemExit("HF_MODEL_REPO_ID is required, for example user/tourism-weather-model.")
    if not args.space_repo_id:
        raise SystemExit("HF_SPACE_REPO_ID is required, for example user/tourism-weather-demo.")

    model_file = args.model_dir / "tourism_weather_extra_trees.joblib"
    metadata_file = args.model_dir / "model_metadata.json"
    sample_file = args.model_dir / "sample_input.json"
    for path in (model_file, metadata_file, sample_file):
        if not path.exists():
            raise SystemExit(f"Missing {path}. Run scripts/train_export_model.py first.")

    api = HfApi(token=args.token)
    api.create_repo(args.model_repo_id, repo_type="model", private=args.private, exist_ok=True)
    api.create_repo(args.space_repo_id, repo_type="space", space_sdk="gradio", private=args.private, exist_ok=True)

    upload_folder(
        repo_id=args.model_repo_id,
        repo_type="model",
        folder_path=str(args.model_dir),
        allow_patterns=["*.joblib", "*.json", "*.csv"],
        token=args.token,
    )

    upload_folder(
        repo_id=args.space_repo_id,
        repo_type="space",
        folder_path=str(args.space_dir),
        token=args.token,
    )

    api.add_space_secret(args.space_repo_id, "HF_MODEL_REPO_ID", args.model_repo_id, token=args.token)
    if args.private:
        api.add_space_secret(args.space_repo_id, "HF_TOKEN", args.token, token=args.token)
    print(f"Model repo: https://huggingface.co/{args.model_repo_id}")
    print(f"Space: https://huggingface.co/spaces/{args.space_repo_id}")


if __name__ == "__main__":
    main()
