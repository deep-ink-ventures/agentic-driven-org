from agents.blueprints.base import command


@command(name="scan-events", description="Scan Lu.ma calendars for upcoming relevant events", schedule="daily")
def scan_events(self, agent) -> dict:
    return {
        "exec_summary": "Scan configured Lu.ma calendars for upcoming events relevant to the project",
        "step_plan": "1. Query all configured Lu.ma calendar URLs\n2. Filter events by relevance to project goals\n3. Extract key details (date, speakers, topics, audience)\n4. Compile event digest with opportunity assessment",
    }
