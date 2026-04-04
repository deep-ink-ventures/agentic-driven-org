"""Step 5: GCS bucket for file storage."""

from deploy.steps.base import BaseStep


class StorageStep(BaseStep):
    name = "storage"
    description = "Create GCS storage bucket"

    def run(self) -> dict:
        return self.provider.create_bucket(
            self.config.project_id,
            self.config.bucket_name,
        )
