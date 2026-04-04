"""Step 4: Memorystore Redis 7."""

from deploy.steps.base import BaseStep


class RedisStep(BaseStep):
    name = "redis"
    description = "Provision Memorystore Redis 7"

    def run(self) -> dict:
        return self.provider.create_redis(
            self.config.project_id,
            self.config.redis_instance_name,
            self.config.vpc_name,
        )
