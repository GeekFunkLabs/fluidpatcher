# FluidPatcher

This package provides a python interface for controlling the versatile, cross-platform, and free [FluidSynth](https://www.fluidsynth.org) software synthesizer. Rather than simply wrapping all the C functions in the FluidSynth API, it provides a higher-level interface for loading and switching between *patches* - groups of settings including:

* soundfonts and presets per channel
* effect settings
* MIDI routing rules
* sequencers, arpeggiators, MIDI file players
* LADSPA effect plugins

Patches are written in YAML format in human-readable and -editable bank files. Bank files can easily be copied and used in FluidPatcher programs written for different platforms and purposes. Two programs are included in the `scripts/` directory of this repository - a command-line synth and a graphical synth/editor. FluidPatcher is the default synth engine used by the [SquishBox](https://geekfunklabs.com/products/squishbox) Raspberry Pi-based sound module.

## Requirements

* [Python](https://python.org/downloads/) >= 3.9
* [PyYAML](https://pypi.org/project/PyYAML/) python package
* [WxPython](https://wxpython.org/pages/downloads/) python package (for `fluidpatcher_gui.pyw`)
* FluidSynth >= 2.2.0, can be obtained in various ways depending on platform:
    * Windows: download latest [release](https://github.com/FluidSynth/fluidsynth/releases) from github and add its location to your Windows `%PATH%`, or copy it to the same folder as your scripts
    * Linux, Mac OS: install using your system's [package manager](https://github.com/FluidSynth/fluidsynth/wiki/Download)
    * [build](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake) the latest version from source

## Installation

Copy the `fluidpatcher/` folder from the github [repository](https://github.com/GeekFunkLabs/fluidpatcher) to to the same directory as any python scripts that use it. For example, to use the included scripts, use the folder structure below:

```shell
scripts/
├── fluidpatcher_gui.pyw
├── fluidpatcher_cli.py
├── config/
│   ├── banks/
│   ├── midi/
│   ├── sf2/
│   └── fluidpatcherconf.yaml
└── fluidpatcher/
```
	
In future, a `setup.py` file or [PyPI](https://pypi.org) package may be available.

## Usage

To understand how to use the included scripts and adjust config files for your system, read [Basic Usage](basic_usage.md).

To learn how to add sounds and create your own patches and bank files, see [Soundfonts](soundfonts.md), [Creating Banks](bank_files.md), and [Plugins](ladspa_plugins.md).

To write your own programs using FluidPatcher, study the [API Reference](api_reference.md) and the code of the included scripts.

## Support

Ask questions, suggest improvements, and/or share your successes in [Discussions](github.com/GeekFunkLabs/fluidpatcher/discussions). If you think you've found a bug, report an [Issue](github.com/GeekFunkLabs/fluidpatcher/issues).
