"""Step registry — ordered list of all provisioning steps."""


def get_steps(config, provider, state) -> list:
    """Return all steps in execution order."""
    from .project import ProjectStep
    from .networking import NetworkingStep
    from .database import DatabaseStep
    from .redis import RedisStep
    from .storage import StorageStep
    from .secrets import SecretsStep
    from .oauth import OAuthStep
    from .registry import RegistryStep
    from .backend import BackendStep
    from .frontend import FrontendStep
    from .celery_vm import CeleryVMStep
    from .dns import DNSStep
    from .service_account import ServiceAccountStep

    step_classes = [
        ProjectStep,
        NetworkingStep,
        DatabaseStep,
        RedisStep,
        StorageStep,
        SecretsStep,
        OAuthStep,
        RegistryStep,
        BackendStep,
        FrontendStep,
        CeleryVMStep,
        DNSStep,
        ServiceAccountStep,
    ]
    return [cls(config, provider, state) for cls in step_classes]
