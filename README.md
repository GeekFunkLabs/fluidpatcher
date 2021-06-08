# FluidPatcher
 A performance-oriented patch interface for [FluidSynth](http://www.fluidsynth.org). Fluidsynth is an open source software synthesizer that uses [soundfonts](https://en.wikipedia.org/wiki/SoundFont) - a [freely-available](https://duckduckgo.com/?q=free+soundfonts) and [well-documented](http://www.synthfont.com/sfspec24.pdf) sound format. A *patch* is a collection of settings such as soundfont presets for each MIDI channel, control-change/sysex messages to send when the patch is selected, and midi router or effects settings. Groups of patches are stored in banks, which are saved as human-readable and -editable [YAML](https://yaml.org/) files. This allows a musician to easily create complex combinations of synthesizer settings ahead of time and switch between them on the fly during a performance.

FluidPatcher should work on any operating system on which FluidSynth and Python can be installed. The *patcher* module controls FluidSynth and handles patches and banks, allowing you to create your own interfaces/implementations so your bank files can be portable and useful in different contexts (e.g. performing, editing, or recording). Several implementations are included:
- *squishbox.py* - runs the [SquishBox](https://www.tindie.com/products/albedozero/squishbox), a Raspberry Pi synth with a 16x2 character LCD and two buttons in a guitar pedal, designed by [Geek Funk Labs](https://geekfunklabs.com/products/squishbox/)
- *headlesspi.py* - runs on a Pi with no screen, keyboard, or extras and allows you to change patches and banks using pads/knobs on your MIDI keyboard/controller
- *fluidpatcher.pyw* - a cross-platform wxpython-based GUI that allows live editing of bank files, playing of patches, and browsing/playing soundfont presets; can also connect to an instance of *squishbox.py* or *headlesspi.py* over a network to control it and edit/test banks.

Check the [wiki](https://github.com/albedozero/fluidpatcher/wiki) for more information about using the scripts, bank/config file formats, the API, etc.

## Installation
Requires [Python 3](https://python.org). Installation of FluidSynth and needed Python modules varies a bit by system.

### Raspberry Pi
You can run a script that will query you for options, then install and configure FluidSynth and FluidPatcher for you by typing the following at a command line:
```
curl https://geekfunklabs.com/squishbox | bash
```
To see what the script does first, eliminate the final `| bash`.

### Windows
Run the setup program in the [latest release](https://github.com/albedozero/fluidpatcher/releases/latest) of FluidPatcher.

### Linux (Debian/Ubuntu)\*
```
sudo apt install git fluidsynth python3-pip python3-wxgtk4.0
sudo pip3 install oyaml mido python-rtmidi
git clone https://github.com/albedozero/fluidpatcher.git
ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 fluidpatcher/SquishBox/sf2/
```

### MacOS\*
```
brew install git fluidsynth python3-pip
sudo pip3 install oyaml mido python-rtmidi wxpython
git clone https://github.com/albedozero/fluidpatcher.git
ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 fluidpatcher/SquishBox/sf2/
```

\* The package repositories on these systems may not provide the latest version of FluidSynth. If you want newer features, it can be [compiled from source](https://github.com/FluidSynth/fluidsynth/wiki/BuildingWithCMake).

## Usage
Bank files are stored in the *SquishBox/banks* directory. The example bank file includes comments to help explain the format and highlight some of the capabilities of patches. Soundfonts are stored in *SquishBox/sf2*. A few sample fonts are provided, and many more can be [found on the internet](https://duckduckgo.com/?q=free+soundfonts) or created/edited/tweaked with software such as [Polyphone](https://www.polyphone-soundfonts.com/). Details on using the included scripts can be found in the [Programs](https://github.com/albedozero/fluidpatcher/wiki/Programs) section of the wiki.

## Example
You can write your own python programs that will use your bank files and patches - the public API is described in the [wiki](https://github.com/albedozero/fluidpatcher/wiki). Here is a simple example:

```python
import patcher

cfgfile = 'myconf.yaml'
bankfile = 'mybank.yaml'
p = patcher.Patcher(cfgfile)
p.load_bank(bankfile)

n = 0
while True:
    p.select_patch(n)
    print("Patch %d/%d: %s" % (n + 1, p.patches_count(), p.patch_name(n)))
    n = int(input("select patch: ")) - 1
```
