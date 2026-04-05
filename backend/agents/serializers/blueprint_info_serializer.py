def get_blueprint_info(agent):
    """Get blueprint info dict for an agent."""
    bp = agent.get_blueprint()
    return {
        "name": bp.name,
        "slug": bp.slug,
        "description": bp.description,
        "tags": bp.tags,
        "default_model": bp.default_model,
        "skills_description": bp.skills_description,
        "commands": bp.get_commands(),
        "config_schema": bp.get_config_json_schema(),
    }
