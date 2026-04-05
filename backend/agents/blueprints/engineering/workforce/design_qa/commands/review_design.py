"""Design QA command: full design QA review of a frontend implementation."""

from agents.blueprints.base import command


@command(
    name="review_design",
    description=(
        "Full design QA review of a frontend implementation. Compares the built UI against the design spec "
        "from UX Designer and checks Impeccable Style compliance (AI Slop Test, all DO/DON'T rules). Applies "
        "Nielsen's 10 heuristics with 0-4 severity scoring (0=no issue, 1=cosmetic, 2=minor, 3=major, "
        "4=catastrophe). Runs cognitive load assessment using the 8-item checklist covering intrinsic, "
        "extraneous, and germane load. Performs persona walkthrough with 5 test personas: Alex the power user, "
        "Jordan the new user, Sam the accessibility-dependent, Riley the stressed/rushing, Casey the non-native "
        "speaker. Output is a structured QA report with severity-scored findings and specific fix instructions. "
        "P0 = blocks ship, P1 = fix before next release, P2 = fix soon, P3 = nice to have."
    ),
    schedule=None,
    model="claude-sonnet-4-6",
)
def review_design(self, agent) -> dict:
    return {
        "exec_summary": "Run full design QA review against design spec, Impeccable Style, heuristics, and persona walkthroughs",
        "step_plan": (
            "1. Retrieve the design spec and acceptance criteria from the originating task\n"
            "2. Retrieve the frontend implementation (PR diff, deployed preview, or screenshots)\n"
            "3. Run AI Slop Test and Impeccable Style DO/DON'T checklist\n"
            "4. Score against Nielsen's 10 heuristics (0-4 severity per heuristic)\n"
            "5. Assess cognitive load (intrinsic, extraneous, germane) with 8-item checklist\n"
            "6. Walk through with 5 personas: Alex, Jordan, Sam, Riley, Casey\n"
            "7. Compile severity-scored findings (P0-P3) with specific fix instructions\n"
            "8. Produce structured QA report"
        ),
    }
