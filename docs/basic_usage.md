# Basic Usage

This section explains how to use the scripts included in this repository, and in general how programs written using FluidPatcher should work. In most cases, one can connect a MIDI keyboard or controller, run a FluidPatcher program, and start playing notes to generate audio. Banks, soundfonts, and midi files can be copied from one program or device to another and provide the same sounds and performances.

## Config Files

A config file allows the user provide settings specific to different programs or platforms, and is also used by programs to store settings and states. Config files are plain text in YAML format, which here means settings are just listed as `<name>: <value>` (the space after `:` is required). The scripts in this repository look for `config/fluidpatcherconf.yaml` by default, but will use a different file if it is passed as a command-line argument.

This is an example config file:

```yaml
bankdir: config/banks
soundfontdir: config/sf2
mfilesdir: config/midi
fluidsettings:
  midi.autoconnect: 1
  player.reset-synth: 0
  synth.gain: 0.6
currentbank: bank1.yaml
```

All settings are optional, unrecognized settings will be ignored, and the order is flexible. Here are the common settings:

* `bankdir` - directory prefix when loading/saving banks; can be relative to the program directory or absolute; defaults to `banks`
* `soundfontdir` - directory prefix for soundfonts; defaults to `{bankdir}/../sf2`
* `mfilesdir` - directory prefix for MIDI files; defaults to `{bankdir}/../midi`
* `plugindir` - directory prefix for LADSPA plugins, see [Plugins](ladspa_plugins.md) for details
* `fluidsettings` - indented list of settings to pass directly to FluidSynth.
* `currentbank` - used by most programs to store the last bank opened, so it can be loaded next time the program starts

FluidSynth maintains a [full list of fluidsynth settings](https://www.fluidsynth.org/api/fluidsettings.xml) with explanations and defaults by platform. Here are some notes on a few important ones:

* `midi.autoconnect` - automatically connects MIDI keyboards/controllers. This does not work on all systems. In some cases (Windows), controllers may need to be connected before the program is started, or connected manually.
* `player.reset-synth` - When playing a MIDI file and reaching the end of a song, all playing notes will be silenced and the synth reset, overriding settings in banks and patches. This is undesirable for FluidPatcher and should be set to 0.
* `synth.gain` - scales the output volume of the synth. This can be in the range 0.0-10.0, but values above 1.0 will be clipped/distorted.
* `synth.polyphony` - If too many voices are played at once (usually by sustaining lots of notes), the CPU may terminate audio while it catches up. This limits the number of active voices, canceling the oldest notes.
* `audio.periods`, `audio.period-size` - These set the number and size of the buffers used for sending digital audio. Lowering these values decreases audio latency (the time between playing a note and hearing the audio), but too low and the sound card won't be able to keep up, producing stuttering/crackling audio.

## fluidpatcher_gui.pyw

This is a desktop (GUI) program that can be used to edit and test bank files, or as a live software synthesizer. The main UI consists of a display showing the current bank and patch, and buttons for switching patches or loading the next available bank. The menus provide options for loading/saving bank files, and selecting patches. The _Tools_ menu provides useful functions:

* _Edit Bank_ - Opens a separate text editor window in which the current bank can be edited directly. Clicking "Apply" will scan the text and update the bank, or pop up a message if there are errors.
* _Choose Preset_ - Opens a soundfont, and allows the user to scroll through and play the soundfont's presets. Double-clicking or clicking _OK_ will paste the selected preset into the bank file.
* _MIDI Monitor_ - Opens a window that will display received MIDI messages
* _Fill Screen_ - Hides the menu bar and maximizes the main UI. Can be useful in live playing.
* _Settings_ - Opens a dialog for viewing and editing the contents of the current config file.

Some program settings, such as the initial height, width, and font size of the UI, can be adjusted by editing the script and changing the values of `WIDTH`, `HEIGHT`, `FONTSIZE`, `PAD`, and/or `FILLSCREEN` at the beginning of the file.

## fluidpatcher_cli.py

This program works from the command line, even in a remote terminal. It lets you load banks, choose patches, and play the synthesizer. The keyboard is used to control the interface and choose options. Here is the list of commands:

* `N` and `P` choose the next/previous patch
* `L` loads the next bank, in alphabetical order
* `M` toggles monitoring of MIDI messages
* `E` opens the current bank in a text editor
* `Q` exits the program

Any other key will print out the list of keyboard commands.