"""Step 2: VPC, subnet, serverless VPC connector, firewall rules."""

from deploy.steps.base import BaseStep


class NetworkingStep(BaseStep):
    name = "networking"
    description = "Create VPC, subnet, VPC connector, firewall rules"

    def run(self) -> dict:
        resources = self.provider.create_vpc(
            self.config.project_id,
            self.config.vpc_name,
            self.config.subnet_name,
        )

        connector = self.provider.create_vpc_connector(
            self.config.project_id,
            self.config.vpc_connector_name,
            self.config.vpc_name,
        )
        resources.update(connector)

        self.provider.create_firewall_rules(
            self.config.project_id,
            self.config.vpc_name,
        )

        return resources
