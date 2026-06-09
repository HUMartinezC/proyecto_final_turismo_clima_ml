#!/usr/bin/env python3
"""Download project datasets from S3 into the local datasets folders.

This script is intentionally independent from ``run_pipeline.py``. It only
loads AWS credentials/configuration from ``.env``, connects to S3 with boto3 and
downloads existing objects from the project lake prefixes.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUCKET = "turismos-clima-ml"
DEFAULT_SOURCES = ("dataestur", "open_meteo", "holidays", "aena")
DEFAULT_LAYERS = ("bronze",)


@dataclass(frozen=True)
class DownloadTask:
    layer: str
    source: str
    s3_prefix: str
    local_base: Path


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def csv_arg(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    items = tuple(item.strip().strip("/") for item in value.split(",") if item.strip())
    return items or default


def boto3_session(region: str | None, profile: str | None):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is not installed. Run `pip install -r requirements.txt`.") from exc

    kwargs: dict[str, str] = {}
    if region:
        kwargs["region_name"] = region

    has_env_credentials = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    if profile and not has_env_credentials:
        kwargs["profile_name"] = profile

    return boto3.Session(**kwargs)


def normalize_prefix(prefix: str) -> str:
    return prefix.strip().strip("/")


def build_tasks(
    layers: tuple[str, ...],
    sources: tuple[str, ...],
    bronze_prefix: str,
    silver_prefix: str,
    gold_prefix: str,
    include_manifests: bool,
) -> list[DownloadTask]:
    tasks: list[DownloadTask] = []
    bronze_dir = PROJECT_ROOT / "datasets" / "bronze"
    processed_dir = PROJECT_ROOT / "datasets" / "processed"

    for layer in layers:
        if layer == "bronze":
            for source in sources:
                tasks.append(
                    DownloadTask(
                        layer=layer,
                        source=source,
                        s3_prefix=f"{bronze_prefix}/{source}/original/",
                        local_base=bronze_dir,
                    )
                )
                if include_manifests:
                    tasks.append(
                        DownloadTask(
                            layer=layer,
                            source=source,
                            s3_prefix=f"{bronze_prefix}/{source}/landing_manifest/",
                            local_base=bronze_dir,
                        )
                    )
        elif layer == "silver":
            for source in sources:
                tasks.append(
                    DownloadTask(
                        layer=layer,
                        source=source,
                        s3_prefix=f"{silver_prefix}/{source}/",
                        local_base=processed_dir / "silver",
                    )
                )
        elif layer == "gold":
            tasks.append(
                DownloadTask(
                    layer=layer,
                    source="gold",
                    s3_prefix=f"{gold_prefix}/",
                    local_base=processed_dir / "gold",
                )
            )
        else:
            raise ValueError(f"Unsupported layer: {layer}")

    return tasks


def local_path_for_key(task: DownloadTask, key: str) -> Path:
    """Map an S3 object key to the local datasets folder for its layer."""
    prefix = task.s3_prefix
    relative = key[len(prefix) :] if key.startswith(prefix) else key

    if task.layer == "bronze":
        bronze_folder = "landing_manifest" if "/landing_manifest/" in task.s3_prefix else "original"
        return task.local_base / task.source / bronze_folder / relative
    if task.layer == "silver":
        return task.local_base / task.source / relative
    if task.layer == "gold":
        return task.local_base / relative
    raise ValueError(f"Unsupported layer: {task.layer}")


def iter_s3_objects(s3_client, bucket: str, prefix: str):
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            yield key, int(obj.get("Size", 0))


def download_prefix(
    s3_client,
    bucket: str,
    task: DownloadTask,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    listed = downloaded = skipped = 0

    for key, size in iter_s3_objects(s3_client, bucket, task.s3_prefix):
        listed += 1
        local_path = local_path_for_key(task, key)

        if local_path.exists() and not overwrite:
            skipped += 1
            print(f"SKIP existing {local_path.relative_to(PROJECT_ROOT)}")
            continue

        print(f"GET s3://{bucket}/{key} -> {local_path.relative_to(PROJECT_ROOT)} ({size} bytes)")
        if not dry_run:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket, key, str(local_path))
        downloaded += 1

    if listed == 0:
        print(f"WARN no objects found under s3://{bucket}/{task.s3_prefix}")

    return listed, downloaded, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download bronze/silver/gold datasets from the project S3 data lake.",
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("S3_BUCKET_NAME", DEFAULT_BUCKET),
        help=f"S3 bucket name. Defaults to S3_BUCKET_NAME or {DEFAULT_BUCKET}.",
    )
    parser.add_argument(
        "--layers",
        default=",".join(DEFAULT_LAYERS),
        help="Comma-separated layers to download: bronze,silver,gold. Default: bronze.",
    )
    parser.add_argument(
        "--sources",
        default=",".join(DEFAULT_SOURCES),
        help="Comma-separated sources for bronze/silver. Default: dataestur,open_meteo,holidays,aena.",
    )
    parser.add_argument("--bronze-prefix", default=os.getenv("S3_BRONZE_PREFIX", "bronze"))
    parser.add_argument("--silver-prefix", default=os.getenv("S3_SILVER_PREFIX", "silver"))
    parser.add_argument("--gold-prefix", default=os.getenv("S3_GOLD_PREFIX", "gold"))
    parser.add_argument("--aws-region", default=os.getenv("AWS_REGION", "eu-west-1"))
    parser.add_argument("--aws-profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument(
        "--include-manifests",
        action="store_true",
        help="Also download bronze landing_manifest prefixes.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite local files if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned downloads without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    bucket = args.bucket
    if not bucket:
        print("ERROR: S3 bucket is required. Set S3_BUCKET_NAME or pass --bucket.", file=sys.stderr)
        return 2

    layers = csv_arg(args.layers, DEFAULT_LAYERS)
    sources = csv_arg(args.sources, DEFAULT_SOURCES)

    valid_layers = {"bronze", "silver", "gold"}
    invalid_layers = sorted(set(layers) - valid_layers)
    if invalid_layers:
        print(f"ERROR: unsupported layers: {', '.join(invalid_layers)}", file=sys.stderr)
        return 2

    tasks = build_tasks(
        layers=layers,
        sources=sources,
        bronze_prefix=normalize_prefix(args.bronze_prefix),
        silver_prefix=normalize_prefix(args.silver_prefix),
        gold_prefix=normalize_prefix(args.gold_prefix),
        include_manifests=args.include_manifests,
    )

    session = boto3_session(region=args.aws_region, profile=args.aws_profile)
    s3_client = session.client("s3")

    total_listed = total_downloaded = total_skipped = 0
    print(f"Bucket: s3://{bucket}")
    print(f"Layers: {', '.join(layers)}")
    print(f"Sources: {', '.join(sources)}")
    print(f"Mode: {'dry-run' if args.dry_run else 'download'}")

    for task in tasks:
        print(f"\n== s3://{bucket}/{task.s3_prefix} ==")
        listed, downloaded, skipped = download_prefix(
            s3_client=s3_client,
            bucket=bucket,
            task=task,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        total_listed += listed
        total_downloaded += downloaded
        total_skipped += skipped

    print("\nDone.")
    print(f"Objects found: {total_listed}")
    print(f"Downloaded/planned: {total_downloaded}")
    print(f"Skipped existing: {total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
