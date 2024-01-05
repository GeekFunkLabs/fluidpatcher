# Soundfonts

Soundfonts are a file format that contains audio samples and parameters that describe instruments based on those samples. The [soundfont specification](http://www.synthfont.com/sfspec24.pdf) defines all the parameters and how synthesizers should interpret them, so that soundfonts will sound the same when used on different software/platforms.

The individual sounds that can be selected from a soundfont are called _presets_. Presets are organized into separate _banks_ each containing up to 128 presets, with _program_ numbers 0-127. Banks can be numbered from 0-16383, but generally only the first few banks are used for instruments, and bank 128 for percussion. Some soundfonts follow the [General Midi](https://www.midi.org/specifications/midi1-specifications/general-midi-specifications) (GM) specification, which defines a set list of instruments they should contain and their preset numbers. Other soundfonts have a random assortment of presets, or just one or two.

## Adding Soundfonts

The soundfonts in the `bankdir` folder and its subfolders, defined in the [config](basic_usage/#config-files) file, are those that will be available to FluidPatcher. You can add soundfonts by copying them to this folder, but to actually play the presets you must add them to a bank file.

Find the `patches` item in a bank file, such as the example below. Each patch begins with an indented name. For each preset you want to use, create a new patch and add the preset with the format `<MIDI channel>: <soundfont file>:<bank>:<program>`. Almost all keyboards will send notes on MIDI channel 1 by default. You can find the bank and program numbers of the presets in the soundfont by opening it with an editor such as the ones listed below. The `fluidpatcher_gui.py` script will list all the presets in a soundfont and let you hear what they sound like before adding them to a patch.

```yaml
patches:
  Bright Piano:
	1: defaultGM.sf2:000:001
  Awesome Guitar Sound:
    1: coolguitars.sf2:000:099
  Spacey Synth:
	1: aliensounds.sf2:2:84
```

## Obtaining Soundfonts

Many soundfonts, both free and paid, are available for download on the internet. A few sites are listed below, and many more can be found with a simple web search.

* [Musical Artifacts](https://musical-artifacts.com/)
* [Polyphone](https://www.polyphone-soundfonts.com/download-soundfonts)
* [RKHive](https://rkhive.com/)

Soundfont editors such as those listed below can be used to modify existing soundfonts, or create them from scratch using audio samples.

* [Swami](http://www.swamiproject.org/)
* [Polyphone](https://www.polyphone-soundfonts.com/)
* [Viena](https://www.softpedia.com/get/Multimedia/Audio/Other-AUDIO-Tools/Viena.shtml)

The `defaultGM.sf2` soundfont included with fluidpatcher is a small GM soundfont that is used in the example bank files included in this repository. If a user desires higher-quality GM sounds, it can be replaced with one of the fonts below by downloading and renaming the file.

* [FluidR3_GM.sf2](https://archive.org/details/fluidr3-gm-gs) (141MB) - pro-quality soundfont created by Frank Wen
* [GeneralUser_GS_1.471.sf2](https://schristiancollins.com/generaluser) (30MB) - lean but high-quality soundfont by S. Christian Collins
