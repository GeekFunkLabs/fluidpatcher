# Installation

FluidPatcher runs on Linux, macOS, and Windows, and requires
**FluidSynth** plus Python 3.10+.

## Install FluidSynth

FluidPatcher talks directly to FluidSynth through `ctypes`, so you will
need the FluidSynth library installed on your system. The
[FluidSynth wiki](https://github.com/FluidSynth/fluidsynth/wiki/Download)
has detailed information on installing/building on various platforms.

* Debian/Ubuntu/Linux Mint
  ```bash
  sudo apt install fluidsynth
  ````

* Fedora / CentOS / RHEL
  ```bash
  sudo dnf install fluidsynth
  ```

* Arch Linux / Manjaro
  ```bash
  sudo pacman -S fluidsynth
  ```

* macOS with [Homebrew](https://brew.sh/)
  ```bash
  brew install fluid-synth
  ```

* Windows
  * Windows Subsystem for Linux (WSL) with Ubuntu,
    follow Linux instructions
  * with [Chocolatey](https://chocolatey.org/) package manager
    ```bash
    choco install fluidsynth
    ```
  * copy [release](https://github.com/FluidSynth/fluidsynth/releases/)
    binary to Windows PATH

To verify the library is visible:
```bash
fluidsynth --version
```

## Install Python package

> It's advised to install in a virtual environment, to avoid breaking
> your system packages.
> 
> ```bash
> python -m venv fpenv
> ```
> 
> To activate your virtual environment:
> 
> ```bash
> source fpenv/bin/activate
> ```

To install from PyPI:

```bash
pip install fluidpatcher
```

To upgrade:

```bash
pip install -U fluidpatcher
```

Or install from source:

```bash
git clone https://github.com/GeekFunkLabs/fluidpatcher.git
cd fluidpatcher
pip install -e .
```

## Optional LADSPA support

FluidPatcher can create LADSPA plugin chains (Linux/macOS) using a small
audio routing plugin `patchcord.so`. This is built or installed from
prebuilt versions when installing the python package. If this fails,
install the LADSPA SDK and re-install the package.

* Debian/Ubuntu/Linux Mint
  ```bash
  sudo apt install ladspa-sdk
  ```
## Verifying Install

You can check that everything is set up correctly by running the
programs in the `examples/` directory.

```bash
python -m fluidpatcher.examples.basic
```

Plug in a MIDI controller and play notes, and you should be able to
hear sounds.

