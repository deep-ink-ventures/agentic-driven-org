"""Email marketing agent commands registry."""
from .check_campaign_performance import check_campaign_performance
from .draft_campaign import draft_campaign
from .send_campaign import send_campaign

ALL_COMMANDS = [check_campaign_performance, draft_campaign, send_campaign]
