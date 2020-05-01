# FluidPatcher
 A performance-oriented patch interface for [FluidSynth](http://www.fluidsynth.org). Fluidsynth is an open source software synthesizer that uses [soundfonts](https://en.wikipedia.org/wiki/SoundFont) - a [freely-available](https://duckduckgo.com/?q=free+soundfonts) and [well-documented](http://www.synthfont.com/sfspec24.pdf) sound format. A *patch* is a collection of settings such as soundfont presets for each MIDI channel, control-change/sysex messages to send when the patch is selected, and midi router or effects settings. Groups of patches are stored in banks, which are saved as human-readable and -editable [YAML](https://yaml.org/) files. This allows a musician to easily create complex combinations of synthesizer settings ahead of time and switch between them on the fly during a performance.

FluidPatcher should work on any operating system on which FluidSynth and Python can be installed. *fluidwrap.py* provides a Python interface to FluidSynth's C functions, and *patcher.py* provides the library functions to handle patches and banks, load soundfonts, change FluidSynth settings, etc. This repository includes the following implementations of *patcher.py*:
- *wxfluidpatcher.pyw* - a wxpython-based GUI that allows live editing of bank files, playing of patches, and browsing/playing soundfont presets.
- *bankedit.py* - a curses-(i.e. text-) based bank editor and patch player.
- *squishbox.py* - a front-end designed to work on a Raspberry Pi with a 16x2 character LCD and two buttons, like the [SquishBox](https://www.tindie.com/products/albedozero/squishbox) designed by [Geek Funk Labs](https://geekfunklabs.com/hardware/).

Check the [wiki](https://github.com/albedozero/fluidpatcher/wiki) for more information about using the scripts, bank/config file formats, the API, etc.

## Installation
Download and install [Python 3](https://python.org). FluidPatcher is not designed to be backwards-compatible with Python 2 (although it will probably work with minor tweaks). If you have Python 2/3 installed side-by-side (e.g. as in most Raspbian distributions), you may have to modify some commands below (e.g. `python` -> `python3` and `pip` -> `pip3`).

Use [pip](http://packaging.python.org/key_projects/#pip) to install dependencies (run as root on Linux/OS X):
```
pip install oyaml wxpython mido python-rtmidi
```
On Windows, add `windows-curses` above for *bankedit.py*.

On a Raspberry Pi, add `RPLCD` and `RPi.GPIO` to use *squishbox.py*.

Install FluidSynth on your system. You can [download packages](https://github.com/FluidSynth/fluidsynth/wiki/Download) for most systems. Precompiled binaries for some platforms are included in the [Releases](https://github.com/albedozero/fluidpatcher/releases) section. Fluidsynth can also be [compiled from source code](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake).

Download the repository and unpack the files where you want to use them. On Windows, the FluidSynth *.dll* files must be in the same directory as FluidPatcher, or their location must be in your *%PATH%* environment variable.

## Usage
The scripts can be run from a command prompt (*Win+R* and `cmd` on Windows). For example
```
python bankedit.py
```
In default Python installations, *.pyw* files will be run as GUI applications as long as the correct Python interpreter is in your path, so double-clicking *wxfluidpatcher.pyw* should work as well.

The *patcherconf.yaml* [config file](https://github.com/albedozero/fluidpatcher/wiki/Config-Files) contains system-wide settings for FluidPatcher. Most flavors of Linux use ALSA as the default sound system as opposed to JACK, which is FluidSynth's default, so you'll want to uncomment the first line below, and perhaps the last two as well:
```
#  audio.driver: alsa
# uncomment/adjust these if latency problems
#  audio.period-size: 64
#  audio.periods: 3
```
Bank files are stored in the *SquishBox/banks* directory. The example bank file includes comments to help explain the format and highlight some of the capabilities of patches. Soundfonts are stored in *SquishBox/sf2*. A few sample fonts are provided, and many more can be found on the internet or created/edited/tweaked with software - such as the excellent [Polyphone](https://www.polyphone-soundfonts.com/). The included *ModWaves.sf2* soundfont demonstrates using modulators in a soundfont to expose FluidSynth's performance capabilities. In this case, control changes (CC) 70 and 74 are mapped to the filter's cutoff and resonance, allowing these to be controlled dynamically with FluidPatcher.