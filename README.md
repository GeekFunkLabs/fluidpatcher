# FluidPatcher


A Python interface for the [FluidSynth](http://www.fluidsynth.org) software synthesizer that lets you create performance patches you can easily switch between while playing. Patches are described in human-readable and -editable [bank files](patcher/file_formats.md), and can be used to create complex combinations of instruments, effects, rules for routing messages from the controls on your MIDI device, play MIDI files, and create sequencers and arpeggiators. Fluidsynth is an open source software synthesizer that uses [soundfonts](https://en.wikipedia.org/wiki/SoundFont) - a [freely-available](https://duckduckgo.com/?q=free+soundfonts) and [well-documented](http://www.synthfont.com/sfspec24.pdf) sound format.

FluidPatcher should work on any platform where FluidSynth and Python can be installed. The [patcher/](patcher/README.md) directory contains all the code to interpret bank files and control FluidSynth, and can be used to create your own interfaces/implementations so your bank files can be portable and useful in different contexts (e.g. performing, editing, recording). Several implementations are included:
- *squishbox.py* - runs the [SquishBox](https://www.tindie.com/products/albedozero/squishbox), a Raspberry Pi synth with a 16x2 character LCD and two buttons in a guitar pedal, designed by [Geek Funk Labs](https://geekfunklabs.com/products/squishbox/)
- *headlesspi.py* - runs on a Pi with no screen, keyboard, or extras and allows you to change patches and banks using pads/knobs on your MIDI keyboard/controller
- *fluidpatcher.pyw* - a cross-platform wxpython-based GUI that allows live editing of bank files in addition to playing patches and browsing/playing soundfont presets

Check the [wiki](https://github.com/albedozero/fluidpatcher/wiki) for more information about using the scripts, bank/config file formats, the API, etc.

## Installation
Requires [Python 3](https://python.org). Installation of FluidSynth and needed Python modules varies a bit by system.

### Raspberry Pi
The install script in the [assets/](assets/) directory will install and configure all the needed software for you! You can easily run it from a command line by entering
```
curl -L git.io/squishbox | bash
```

### Windows
Run the setup program in the [latest release](https://github.com/albedozero/fluidpatcher/releases/latest) of FluidPatcher.

### Linux (Debian/Ubuntu)\*
```
sudo apt install git libfluidsynth fluid-soundfont-gm python3-pip python3-rtmidi python3-wxgtk4.0
sudo pip3 install oyaml mido
git clone https://github.com/albedozero/fluidpatcher.git
ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 fluidpatcher/SquishBox/sf2/
```

### MacOS\*
```
brew install git libfluidsynth fluid-soundfont-gm python3-pip
sudo pip3 install oyaml mido python-rtmidi wxpython
git clone https://github.com/albedozero/fluidpatcher.git
ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 fluidpatcher/SquishBox/sf2/
```

\* The package repositories on these systems may not provide the latest version of FluidSynth. If you want newer features, it can be [compiled from source](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake).

## Usage
[Bank files](https://github.com/albedozero/fluidpatcher/blob/master/patcher/file_formats.md#bank-files) are stored in the *SquishBox/banks* directory. The example bank file includes comments to help explain the format and highlight some of the capabilities of patches. Soundfonts are stored in *SquishBox/sf2*. A few sample fonts are provided, and many more can be [found on the internet](https://duckduckgo.com/?q=free+soundfonts) or created/edited/tweaked with software such as [Polyphone](https://www.polyphone-soundfonts.com/). Details on setting up/using the included scripts can be found in [programs.md](programs.md).
