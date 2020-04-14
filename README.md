# FluidPatcher
 A performance-oriented patch interface for [FluidSynth](http://www.fluidsynth.org). Fluidsynth is a software synthesizer that uses [soundfonts](https://en.wikipedia.org/wiki/SoundFont) - a [freely-available](https://duckduckgo.com/?q=free+soundfonts) and [well-documented](http://www.synthfont.com/sfspec24.pdf) sound format. A *patch* is a collection of settings such as soundfont presets for each MIDI channel, control-change/sysex messages to send when the patch is selected, and midi router or effects settings. Groups of patches are stored in banks, which are saved as human-readable and -editable [YAML](https://yaml.org/) files. This allows a musician to easily create complex combinations of synthesizer settings ahead of time and switch between them on the fly during a performance.

FluidPatcher should work on any operating system on which FluidSynth and [Python](https://python.org) (3.5+) can be installed. *fluidwrap.py* provides a Python interface to FluidSynth's C functions, and *patcher.py* provides the library functions to handle patches and banks, load soundfonts, change FluidSynth settings, etc. This repository includes two implementations of *patcher.py*. *SquishBox* is designed specifically for a Raspberry Pi enclosed in a stompbox with an LCD and two buttons. *BankEdit* is a text-based Patcher interface that allows live playing and editing of bank files. Consult the [wiki](https://github.com/albedozero/fluidpatcher/wiki) for more info about using SquishBox or BankEdit and creating bank files. More information about the SquishBox can be found at [Geek Funk Labs](https://geekfunklabs.com/hardware/).

## Installation
This assumes you only have Python 3 installed on your system. If you have Python 2/3 installed side-by-side, you may have to tweak some commands below (e.g. `pip` -> `pip3`).

Use [pip](http://packaging.python.org/key_projects/#pip) to install dependencies (run as root on Linux/OS X):
```
pip install oyaml mido
```
On Windows, add `windows-curses` above to enable the text interface.

Obtain FluidSynth somehow. On Windows, the easiest way is by installing a GUI front-end such as [QSynth](https://qsynth.sourceforge.io/). On Debian-like (e.g. Raspbian) systems:
```
sudo apt-get install fluidsynth
```
Download the repository and unpack the files where you want to use them. On Windows, `ctypes` seems to have trouble finding the FluidSynth libraries, so you may need to unpack into your QSynth/FluidSynth folder, or copy the relevant *.dll* files into the same directory as FluidPatcher.

## Usage
If on Linux, you'll want to uncomment the first line below in *bankeditconf.yaml*, and perhaps the others as well:
```
#  audio.driver: alsa
# uncomment/adjust these if latency problems
#  audio.period-size: 64
#  audio.periods: 3
```
In a terminal window or at a command prompt (*Win+R* and `cmd` on Windows), type
```
python bankedit.py
```
A very simple text-based editor opens, allowing you to play patches from and make changes to the current bank. Some copy+paste functionality may be available, depending on the type of terminal window/command prompt. The current changes to the bank can be "refreshed" at any time to test them, banks can be loaded and saved, and single soundfonts can be loaded to browse through for sounds.
