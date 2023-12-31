# FluidPatcher

This package provides a python interface for controlling the versatile, cross-platform, and free [FluidSynth](http://www.fluidsynth.org) software synthesizer. Rather than simply wrapping all the C functions in the FluidSynth API, it provides a higher-level interface for loading and switching between *patches* - groups of settings including:

- soundfonts and presets per channel
- effect settings
- MIDI routing rules
- sequencers, arpeggiators, MIDI file players
- LADSPA effect plugins

Patches are written in YAML format in human-readable and -editable bank files. Bank files can easily be copied and used in FluidPatcher programs written for different platforms and purposes. Two programs are included in the *scripts/* directory of this repository - a command-line synth and a graphical synth/editor. FluidPatcher is the default synth engine used by the [SquishBox](https://www.geekfunklabs.com/products/squishbox) Raspberry Pi-based sound module.

## Requirements

- [Python](https://www.python.org/downloads/) >= 3.9
- [PyYAML](https://pypi.org/project/PyYAML/) python package
- [WxPython](https://wxpython.org/pages/downloads/) python package (for *fluidpatcher_gui*)
- FluidSynth >= 2.2.0, can be obtained in various ways depending on platform:
    - Windows: download latest [release](https://github.com/FluidSynth/fluidsynth/releases) from github
    - Linux, Mac OS: install using your system's [package manager](https://github.com/FluidSynth/fluidsynth/wiki/Download)
    - [build](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake) the latest version from source

## Installation

Copy the *fluidpatcher/* directory from the github [repository](https://github.com/GeekFunkLabs/fluidpatcher) to a location in your system python's or virtual environment's module search path, or where it can be imported by any python programs that need it. To use the included scripts, copy the contents of the *scripts/* directory to a convenient location. In future, a setup.py or pypi package may be available.

## Usage

Instructions for modifying configuration files for your system and using the included scripts are in the [Programs](programs.md) section.

To learn how to create your own patches and bank files, read the [Bank Files](bank_files.md) section.

To understand how to create your own programs using FluidPatcher, study the code of the included scripts and check the [API Reference](api_reference.md).

## Support

Ask questions, suggest improvements, and/or share your successes in [Discussions](https://github.com/GeekFunkLabs/fluidpatcher/discussions). If you think you've found a bug, report an [Issue](https://github.com/GeekFunkLabs/fluidpatcher/issues).

