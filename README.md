# FluidPatcher
 A performance-oriented patch interface for [FluidSynth](http://www.fluidsynth.org). Fluidsynth is an open source software synthesizer that uses [soundfonts](https://en.wikipedia.org/wiki/SoundFont) - a [freely-available](https://duckduckgo.com/?q=free+soundfonts) and [well-documented](http://www.synthfont.com/sfspec24.pdf) sound format. A *patch* is a collection of settings such as soundfont presets for each MIDI channel, control-change/sysex messages to send when the patch is selected, and midi router or effects settings. Groups of patches are stored in banks, which are saved as human-readable and -editable [YAML](https://yaml.org/) files. This allows a musician to easily create complex combinations of synthesizer settings ahead of time and switch between them on the fly during a performance.

FluidPatcher should work on any operating system on which FluidSynth and Python can be installed. The *patcher/* module creates a Python wrapper around FluidSynth's C functions and provides an API to handle patches and banks, load soundfonts, change FluidSynth settings, etc. This repository includes the following implementations of FluidPatcher:
- *squishbox.py* - a front-end designed to work on a Raspberry Pi with a 16x2 character LCD and two buttons, like the [SquishBox](https://www.tindie.com/products/albedozero/squishbox) designed by [Geek Funk Labs](https://geekfunklabs.com/hardware/)
- *headlesspi.py* - a simple implementation that can run at startup on a bare-bones Raspberry Pi with no screen or keyboard
- *wxfluidpatcher.pyw* - a cross-platform wxpython-based GUI that allows live editing of bank files, playing of patches, and browsing/playing soundfont presets; can also connect to an instance of *squishbox.py* or *headlesspi.py* to control it and edit/test banks.

Check the [wiki](https://github.com/albedozero/fluidpatcher/wiki) for more information about using the scripts, bank/config file formats, the API, etc.

## Installation
Download and install [Python 3](https://python.org). FluidPatcher is not designed to be backwards-compatible with Python 2 (although it will probably work with minor tweaks). Some systems (e.g. Raspberry Pi OS), already have Python 2 installed, so be aware commands may be modified to differentiate them (e.g. `python` -> `python3` and `pip` -> `pip3`). Then, use [pip](http://packaging.python.org/key_projects/#pip) to install additional needed Python packages. Finally, obtain FluidSynth. You can [download packages](https://github.com/FluidSynth/fluidsynth/wiki/Download) for most systems. On Windows you can download a release FluidPatcher bundled with a precompiled binary of FluidSynth from [GitHub](https://github.com/albedozero/fluidpatcher/releases) or [SourceForge](https://sourceforge.net/projects/fluidpatcher/). If you want the latest and greatest Fluidsynth, it's also fairly easy to [compile from source code](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake).

### Quick Install by System

#### Windows
Run the setup program in the [release](https://github.com/albedozero/fluidpatcher/releases) of FluidPatcher. Install Python 3 - *pip* is included with most distributions. Enter the following on a command line to install Python modules:
```
pip install oyaml wxpython mido python-rtmidi
```

#### Linux
```
sudo apt install git fluidsynth python3-pip python3-wxgtk4.0
sudo pip3 install oyaml mido python-rtmidi
git clone https://github.com/albedozero/fluidpatcher.git
cp -r fluidpatcher/* /home/pi
```
On a Raspberry Pi, add `sudo pip3 install RPLCD RPi.GPIO`.

#### MacOS
```
brew install fluidsynth git python3-pip
sudo pip3 install oyaml mido python-rtmidi wxpython
git clone https://github.com/albedozero/fluidpatcher.git
```

## Usage
Double click the *wxfluidpatcher.py* script or the FluidPatcher shortcut created by the installer. FluidSynth must be in your path or in the same directory as FluidPatcher. The *patcherconf.yaml* [config file](https://github.com/albedozero/fluidpatcher/wiki/Config-Files) contains system-wide settings.

Bank files are stored in the *SquishBox/banks* directory. The example bank file includes comments to help explain the format and highlight some of the capabilities of patches. Soundfonts are stored in *SquishBox/sf2*. A few sample fonts are provided, and many more can be found on the internet or created/edited/tweaked with software - such as the excellent [Polyphone](https://www.polyphone-soundfonts.com/). The included *ModWaves.sf2* soundfont demonstrates using modulators in a soundfont to expose FluidSynth's performance capabilities. In this case, control changes (CC) 70 and 74 are mapped to the filter's cutoff and resonance, allowing these to be controlled dynamically with FluidPatcher.


## Example
You can write your own python programs that will use your bank files and patches - the public API is described in the [wiki](https://github.com/albedozero/fluidpatcher/wiki). Here is a simple example:

```python
import patcher

cfgfile = 'patcherconf.yaml'
p = patcher.Patcher(cfgfile)
p.load_bank()

n = 0
while True:
    p.select_patch(n)
    print("Patch %d/%d: %s" % (n + 1, p.patches_count(), p.patch_name(n)))
    n = int(input("select patch: ")) - 1
```
First, FluidPatcher is started by creating a Patcher instance with a [config file](Config-Files) as its argument, describing where [bank files](Bank-Files) and soundfonts are stored, the name of the first bank file to load, and what settings to pass to FluidSynth on startup. This starts FluidSynth in a separate thread. When `load_bank` is called with no arguments, it loads the last bank used. The function `select_patch` will accept a number or the patch name. Most recent versions of FluidSynth will automatically connect to any attached MIDI input devices, so playing notes on an attached controller will make sounds according to the selected patch from the loaded bank file.
