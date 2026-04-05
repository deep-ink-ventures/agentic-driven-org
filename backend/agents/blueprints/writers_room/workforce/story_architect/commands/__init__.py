"""Story Architect agent commands registry."""

from .develop_concept import develop_concept
from .fix_structure import fix_structure
from .generate_concepts import generate_concepts
from .map_subplot_threads import map_subplot_threads
from .outline_act_structure import outline_act_structure
from .write_structure import write_structure

ALL_COMMANDS = [
    write_structure,
    fix_structure,
    outline_act_structure,
    map_subplot_threads,
    generate_concepts,
    develop_concept,
]
