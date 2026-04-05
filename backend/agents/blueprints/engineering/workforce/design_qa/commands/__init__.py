"""Design QA Specialist agent commands registry."""

from .check_accessibility import check_accessibility
from .check_consistency import check_consistency
from .check_responsive import check_responsive
from .review_design import review_design

ALL_COMMANDS = [review_design, check_accessibility, check_responsive, check_consistency]
