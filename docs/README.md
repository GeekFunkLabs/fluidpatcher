# FluidPatcher

This package provides a way of controlling the many features of the [FluidSynth](https://www.fluidsynth.org) software synthesizer by creating *patches*. A patch is a group of settings that can be applied all at once, quickly switched between, and easily edited - like instantly rearranging the patch cables on a modular synthesizer. Patches are defined in human-readable YAML-based text files called banks, which can contain an unlimited number of patches. Patches have the capability to: 

* select soundfont presets on any channel
* define MIDI routing rules
* send MIDI messages
* create and control sequencers, arpeggiators, and MIDI file players
* manage LADSPA effect plugins
* control internal Fluidsynth settings

FluidPatcher has a simple API that can be used to create different synthesizer front-end programs that use the same bank files. Example programs are  included in the `scripts/` directory of this repository.

See the [official documentation](https://geekfunklabs.github.io/fluidpatcher) for full details.

## Requirements

* [Python](https://python.org/downloads/) >= 3.9
* [PyYAML](https://pypi.org/project/PyYAML/) python package
* FluidSynth >= 2.2.0, can be obtained in various ways depending on platform:
    * Windows: download latest [release](https://github.com/FluidSynth/fluidsynth/releases) from github and add its location to your Windows `%PATH%`, or copy it to the same folder as your scripts
    * Linux, Mac OS: install using your system's [package manager](https://github.com/FluidSynth/fluidsynth/wiki/Download)
    * [build](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake) the latest version from source

## Installation

Copy the `fluidpatcher/` folder from the github [repository](https://github.com/GeekFunkLabs/fluidpatcher) to to the same directory as any python scripts that use it. For example, to use the included scripts, use the folder structure below:

```shell
📁 scripts/
├── 📄 fluidpatcher_gui.pyw
├── 📄 fluidpatcher_cli.py
├── 📁 config/
│   ├── 📁 banks/
│   ├── 📁 midi/
│   ├── 📁 sf2/
│   └── 📄 fluidpatcherconf.yaml
└── 📁 fluidpatcher/
```

In future, a `setup.py` file or [PyPI](https://pypi.org) package may be available.

## Usage

To understand how to use the included scripts and adjust config files for your system, read [Basic Usage](basic_usage.md).

To learn how to add sounds and create your own patches and bank files, see [Soundfonts](soundfonts.md), [Creating Banks](bank_files.md), and [Plugins](ladspa_plugins.md).

To write your own programs using FluidPatcher, study the [API Reference](api_reference.md) and the code of the included scripts.

## Support

Ask questions, suggest improvements, and/or share your successes in [Discussions](github.com/GeekFunkLabs/fluidpatcher/discussions). If you think you've found a bug, report an [Issue](github.com/GeekFunkLabs/fluidpatcher/issues).
