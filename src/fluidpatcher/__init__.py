"""Performance-oriented patch management for FluidSynth.

FluidPatcher provides a high-level interface to the FluidSynth
software synthesizer, organized around *patches* stored in YAML
bank files. Each patch can define instruments, controller values,
LADSPA effects, MIDI sequences, router rules, and more.

Key components:
  - patcher.py - user-facing API for loading banks, applying patches
  - bankfiles.py – YAML extensions and helpers for parsing banks
  - config.py - configuration loading and initialization
  - router.py – live MIDI routing and rule processing
  - pfluidsynth.py – ctypes bindings and custom implementations
    as lightweight wrappers around FluidSynth objects

Typical usage:

    fp = FluidPatcher()
    fp.load_bank("mybank.yaml")
    fp.apply_patch("Warm Pad")

Requirements:
  - PyYAML
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

