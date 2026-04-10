"""Out-of-Box Thinker command: propose cross-domain fields for problem solving."""

from agents.blueprints.base import command


@command(
    name="propose-fields",
    description=(
        "Propose 5 cross-domain fields via bisociation: 2 same-domain, "
        "2 associated-domain, 1 random-associative. Must not repeat fields from prior rounds."
    ),
    model="claude-opus-4-6",
)
def propose_fields(self, agent) -> dict:
    return {
        "exec_summary": "Propose 5 cross-domain fields for hypothesis exploration",
        "step_plan": (
            "1. Review the problem decomposition and definition of done\n"
            "2. Review prior round history — which fields were tried and their scores\n"
            "3. Propose 2 same-domain fields (e.g. two math subfields)\n"
            "4. Propose 2 associated-domain fields (related but distinct disciplines)\n"
            "5. Propose 1 random-associative field (unexpected domain with structural similarity)\n"
            "6. For each field, explain the structural analogy to the problem"
        ),
    }
