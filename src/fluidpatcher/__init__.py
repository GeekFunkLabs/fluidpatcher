"""A performance-oriented patch interface for FluidSynth

A Python interface for the FluidSynth software synthesizer that
allows combination of instrument settings, effects, sequences,
midi file players, etc. into performance patches that can be
quickly switched while playing. Patches are written in a rich,
human-readable YAML-based bank file format.

Requires:
- yaml
- libfluidsynth
"""

from importlib.metadata import version, PackageNotFoundError

from .bankfiles import MidiMessage, MidiRule, SFPreset
from .config import CONFIG, save_config
from .patcher import FluidPatcher
from .pfluidsynth import FluidMidiEvent


__all__ = ["MidiMessage", "MidiRule", "SFPreset", "CONFIG",
           "save_config", "FluidPatcher", "FluidMidiEvent"]

try:
    __version__ = version("fluidpatcher")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

