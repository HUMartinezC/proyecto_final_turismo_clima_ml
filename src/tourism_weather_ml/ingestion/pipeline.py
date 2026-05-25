from tourism_weather_ml.aws.clients import AwsClients
from tourism_weather_ml.config import Settings
from tourism_weather_ml.ingestion.dataestur import DataesturClient
from tourism_weather_ml.ingestion.sources import IDEAL_SOURCES


class IngestionPipeline:
    def __init__(self, settings: Settings, clients: AwsClients) -> None:
        self.settings = settings
        self.clients = clients

    def run(
        self,
        dry_run: bool = True,
        source_name: str | None = None,
        dataestur_endpoints: tuple[str, ...] | None = None,
        dataestur_limit: int | None = None,
    ) -> list[str]:
        actions: list[str] = []
        bucket = self.settings.s3_bucket_name or "<S3_BUCKET_NAME>"

        for source in IDEAL_SOURCES:
            if source_name and source.name != source_name:
                continue
            if source.name == "dataestur":
                key = f"{self.settings.s3_bronze_prefix}/{source.name}/original/"
                actions.append(f"ingest {source.name} ({source.grain}) into s3://{bucket}/{key}")
                dataestur = DataesturClient(self.settings, self.clients)
                if dry_run:
                    plans = dataestur.plan_configured_sources(
                        endpoints=dataestur_endpoints,
                        limit=dataestur_limit,
                    )
                    actions.extend(
                        (
                            f"plan Dataestur {item.name}: GET {item.url} -> "
                            f"{item.local_dir}/ and {item.s3_bronze_original_prefix}; "
                            f"bronze manifest -> {item.s3_bronze_manifest_prefix}"
                        )
                        for item in plans
                    )
                    continue
                try:
                    downloads = dataestur.download_configured_sources(
                        endpoints=dataestur_endpoints,
                        limit=dataestur_limit,
                    )
                except Exception as exc:
                    actions.append(f"skipped Dataestur download after error: {exc}")
                    continue
                if downloads:
                    actions.extend(
                        f"downloaded Dataestur {item.name} to {item.local_path}"
                        + (
                            f"; bronze_original=s3://{self.settings.s3_bucket_name}/"
                            f"{item.s3_bronze_original_key}"
                            f"; bronze_manifest=s3://{self.settings.s3_bucket_name}/"
                            f"{item.s3_bronze_manifest_key}"
                            if item.s3_bronze_original_key and item.s3_bronze_manifest_key
                            else ""
                        )
                        for item in downloads
                    )
                    continue
                actions.append(
                    "skipped Dataestur download: configure DATAESTUR_ENDPOINTS, "
                    "DATAESTUR_EOH_REQUEST_URL or DATAESTUR_EXTRA_REQUEST_URLS"
                )
                continue
            if source_name:
                actions.append(f"skipped {source.name}: ingestion connector is not implemented yet")
                continue
            if dry_run:
                actions.append(f"plan {source.name}: connector not implemented yet, no external call")
                continue
            actions.append(f"skipped {source.name}: ingestion connector is not implemented yet")

        return [f"DRY-RUN {action}" if dry_run else action for action in actions]
