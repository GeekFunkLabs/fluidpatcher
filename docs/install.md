# Installation

FluidPatcher runs on Linux, macOS, and Windows, and requires
**FluidSynth** plus Python 3.10+.

## Install FluidSynth

FluidPatcher talks directly to FluidSynth through `ctypes`, so you will
need the FluidSynth library installed on your system. The
[FluidSynth wiki](https://github.com/FluidSynth/fluidsynth/wiki/Download)
has detailed information on installing/building on various platforms.

* Debian/Ubuntu/Linux Mint

``` bash
sudo apt install fluidsynth
```

* Fedora / CentOS / RHEL

```
sudo dnf install fluidsynth
```

* Arch Linux / Manjaro

```
sudo pacman -S fluidsynth
```

* macOS with [Homebrew](https://brew.sh/)

```
brew install fluid-synth
```

* Windows

    * Windows Subsystem for Linux (WSL) with Ubuntu,
      follow Linux instructions

    * With [Chocolatey](https://chocolatey.org/) package manager

      ```
      choco install fluidsynth
      ```

    * Copy [release](https://github.com/FluidSynth/fluidsynth/releases/)
      binary, add its location to PATH

To verify the library is visible:
```
fluidsynth --version
```

## Optional LADSPA support

FluidPatcher can construct LADSPA effect plugin chains (Linux/macOS)
and route audio from MIDI channels separately through plugins. Plugins
are obtained and installed separately from FluidSynth. The
LADSPA SDK provides support for building, discovering, and analyzing
plugins.

* Debian/Ubuntu/Linux Mint
  ```
  sudo apt install ladspa-sdk
  ```

## Install Python package

!!! note
    It's advised to install in a virtual environment, to avoid breaking
    your system packages. For example:

    ```
    python -m venv fpenv
    ```

    To activate your virtual environment:

    ```
    source fpenv/bin/activate
    ```

To install from PyPI:

```
python -m pip install fluidpatcher
```

To upgrade:

```
python -m pip install -U fluidpatcher
```

Or install from source:

```
git clone https://github.com/GeekFunkLabs/fluidpatcher.git
cd fluidpatcher
python -m pip install -e .
```

## Verifying Install

You can check that everything is set up correctly by running the
programs in the `examples/` directory.

```
python -m fluidpatcher.examples.basic
```

Plug in a MIDI controller and play notes, and you should be able to
hear sounds.

