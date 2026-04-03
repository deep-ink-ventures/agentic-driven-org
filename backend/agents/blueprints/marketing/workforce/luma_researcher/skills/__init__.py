"""Lu.ma researcher agent skills registry."""
import importlib
import pkgutil

SKILLS = []

# Auto-discover all skill modules in this package
for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
