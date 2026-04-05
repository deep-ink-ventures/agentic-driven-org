"""Lead Writer commands registry."""

from .write_concept import write_concept
from .write_expose import write_expose
from .write_first_draft import write_first_draft
from .write_pitch import write_pitch
from .write_treatment import write_treatment

ALL_COMMANDS = [write_pitch, write_expose, write_treatment, write_concept, write_first_draft]
