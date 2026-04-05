from agents.blueprints.base import command


@command(
    name="check-campaign-performance",
    description=(
        "Retrieve SendGrid stats for all campaigns sent in the last 7 days and benchmark against industry "
        "standards (open rate >20%, CTR >2.5%, unsubscribe <0.5%, bounce <2%). Performs cohort analysis "
        "comparing subject line variants, send times, and audience segments to identify top performers. "
        "Produces actionable recommendations for future campaigns including specific subject line, timing, "
        "and segmentation adjustments backed by the data."
    ),
    schedule="daily",
)
def check_campaign_performance(self, agent) -> dict:
    return {
        "exec_summary": "Check recent email campaign performance metrics (opens, clicks, unsubscribes, bounces)",
        "step_plan": (
            "1. Retrieve stats for all campaigns sent in the last 7 days via SendGrid API\n"
            "2. Calculate open rate, click-through rate, bounce rate, and unsubscribe rate\n"
            "3. Compare metrics against previous period and industry benchmarks\n"
            "4. Identify top-performing and underperforming campaigns\n"
            "5. Generate actionable recommendations for future campaigns"
        ),
    }
