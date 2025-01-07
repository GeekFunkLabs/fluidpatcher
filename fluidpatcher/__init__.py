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

__version__ = '1.0.0'

from .patcher import FluidPatcher
from .bankfiles import SFPreset, MidiMessage, RouterRule
