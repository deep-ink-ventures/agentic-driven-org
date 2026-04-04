"""Base class for provisioning steps."""

from abc import ABC, abstractmethod

from rich.console import Console

from deploy.config import TenantConfig
from deploy.providers.base import CloudProvider
from deploy.state import is_step_complete, mark_step_complete, save_state

console = Console()


class BaseStep(ABC):
    """A single provisioning step."""

    name: str = ""  # Override in subclass
    description: str = ""  # Override in subclass

    def __init__(self, config: TenantConfig, provider: CloudProvider, state: dict) -> None:
        self.config = config
        self.provider = provider
        self.state = state

    def execute(self) -> None:
        """Run the step, skipping if already completed."""
        if is_step_complete(self.state, self.name):
            console.print(f"[green]✓[/green] {self.description} [dim](already done)[/dim]")
            return

        console.print(f"\n[bold blue]→ {self.description}[/bold blue]")
        resources = self.run()
        mark_step_complete(self.state, self.name, resources)
        save_state(self.config.company, self.state)
        console.print(f"[green]✓[/green] {self.description} [green]complete[/green]")

    @abstractmethod
    def run(self) -> dict | None:
        """Execute the step. Return resource identifiers to store in state."""
        ...
