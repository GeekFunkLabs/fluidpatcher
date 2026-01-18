# FluidPatcher

FluidPatcher is a lightweight Python toolkit for building playable
FluidSynth-based instruments driven by MIDI events. It provides:

* A simple user-facing API for building applications/front-ends
* Rich YAML-based bank/patch file format for defining synth setups
* Support for multiple soundfonts, layered MIDI routing, and rules
* Built-in players (arpeggiators, sequencers, MIDI files, loopers)
* Optional LADSPA audio effects

FluidPatcher is designed for small systems such as Raspberry Pi but runs
anywhere FluidSynth does. Banks are designed to be portable to different
programs/platforms. Sample programs are in `examples/`.

See the [official documentation](
  https://geekfunklabs.github.io/fluidpatcher
) for full details.


## Installation

### System Requirements
* Python 3.9+
* PyYAML
* [FluidSynth](
  https://github.com/FluidSynth/fluidsynth/wiki/Download
) 2.2.0+
```bash
  sudo apt install fluidsynth
```
* Optional audio effects:
```bash
  sudo apt install ladspa-sdk
```

### Install FluidPatcher

```bash
pip install fluidpatcher
```

Or install from source:

```bash
git clone https://github.com/GeekFunkLabs/fluidpatcher.git
cd fluidpatcher
pip install -e .
```

## Configuration

FluidPatcher looks for config at `FLUIDPATCHER_CONFIG` if defined, or
`~/.config/fluidpatcher/fluidpatcherconf.yaml`. A default config is
created if not found. The config file can be used to store/specify:

* Paths for soundfonts, bank files, MIDI files, LADSPA effects
* FluidSynth [settings](
    https://www.fluidsynth.org/api/fluidsettings.xml
  )
  e.g. audio driver/device if other than default
* State information for specific programs

## API Overview/Quick Start

```python
import fluidpatcher

fp = fluidpatcher.FluidPatcher()
fp.load_bank("mybank.yaml")
fp.apply_patch("Piano")
```

Play notes on an attached MIDI controller to hear patches. By default,
FluidSynth will automatically connect to MIDI devices.

## Banks & Patches

Bank files provide a declarative, YAML-based language for describing
synth *patches*. The underlying engine parses bank files and pre-loads
required soundfonts so that different patches can be applied quickly in
live performance. View the Tutorials section in the docs and/or example
banks for guided learning:

```shell
📁 data/banks/tutorial
├── 📄 lesson01_basic.yaml     # bank/patch structure
├── 📄 lesson02_messages.yaml  # init blocks & sending messages
├── 📄 lesson03_rules.yaml     # router rules + transformations
├── 📄 lesson04_players.yaml   # arps, sequences, file players, loopers
└── 📄 lesson05_effects.yaml   # LADSPA effects
```

## Status & Contributions

FluidPatcher is under active development. The goal is to keep the API
minimalist and general, with most features/functionality implemented in
bank files or external programs. Contributions, bug reports, and example
banks are welcome.

Please open issues or pull requests on GitHub.

## License

MIT. See LICENSE for details.

