"""Game design mapping intelligence for Clone Hero."""

from src.game_design.chord_builder import ChordBuilder
from src.game_design.hopo_engine import HopoEngine
from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import NoteQuantizer, QuantizedNote
from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor

__all__ = [
    "ChordBuilder",
    "HopoEngine",
    "NoteQuantizer",
    "PitchToFretMapper",
    "QuantizedNote",
    "StarPowerGenerator",
    "SustainProcessor",
]
