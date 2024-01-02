# Basic Usage

## Config Files

Programs that use fluidpatcher can use a 

Config files have the following structure:

```yaml
soundfontdir: <root path where soundfonts are stored {sf2}>
bankdir: <root path where bank files are stored {banks}>
mfilesdir: <location of MIDI files {''}>
plugindir: <location of LADSPA effects {''}>
currentbank: <last bank loaded {''}>
fluidsettings:
  <name1>: <value1>
  <name2>: <value2>
  ...
```

All settings are optional, and the order is flexible. The Patcher will use the default values shown in curly braces above if the settings aren't given or a config file isn't provided. The settings in `fluidsettings` are passed directly to fluidsynth. A full list of fluidsynth settings is at [fluidsynth.org/api/fluidsettings.xml](http://www.fluidsynth.org/api/fluidsettings.xml), any that aren't specified in the config file will be given the default value based on platform. Fluidsynth settings in the config file are applied when the synth is first activated and each time a bank file is loaded. Only the settings in the node with the exact name `fluidsettings` will be used - nodes with similar names may be included in the config file to store alternative setups.

Here are a few (a bit technical) notes about some of the fluidsettings that can be useful in config files:
- `audio.driver` - the audio driver to use. Varies by platform.
- `audio.periods` and `audio.period-size` - controls the amount of buffer space available for the audio driver. Has no effect on `jack`, which uses the _/etc/jackdrc_ or _$HOME/.jackdrc_ file as explained on the [jackd manpage](https://linuxcommandlibrary.com/man/jackd#environment).
- `midi.autoconnect` - set this to 1 to have fluidsynth automatically connect to MIDI controllers when they are plugged in.
- `player.reset-synth` - if set to 1, when playing a MIDI file fluidsynth will reset completely when it reaches the end of the song, stopping all sound output and overriding fluidpatcher's settings. If you don't want this, set it to 0
- `synth.polyphony` - if you play too many voices at once (usually by sustaining lots of notes) fluidsynth will have to stop audio while the processor catches up. This limits the number of active voices, cancelling the oldest notes.
- `synth.audio.groups` - the number of internal stereo audio buffers to create. MIDI channels are routed sequentially to each audio group, wrapping around if there are fewer groups than channels. One use of this is to create separate mixer groups for routing LADSPA effect plugins.
- `synth.gain` - scales the output volume of the synth. This can be in the range 0.0-10.0, but values above 1.0 will be clipped/distorted.

## fluidpatcher_gui

_Fluidpatcher.pyw_ is a desktop (GUI) program that should work on any platform (Windows, Linux, MacOS) where Python 3 and FluidSynth can be installed. It can be used to play patches in a live setting, and also to edit bank files and immediately hear the results.

The _fluidpatcher.pyw_ script takes a config file as its argument, otherwise it will use _fluidpatcherconf.yaml_ by default. The main UI consists of a display showing the current bank and patch, and buttons for switching patches or loading the next available bank. The menus provide options for loading/saving bank files, and selecting patches. The _Tools_ menu provides useful features:

- _Edit Bank_ - Opens a separate text editor window in which the current bank can be edited directly. Clicking "Apply" will scan the text and update the bank, or pop up a message if there are errors.
- _Choose Preset_ - Opens a soundfont, and allows the user to scroll through and play the soundfont's presets. Double-clicking or clicking "OK" will paste the selected preset into the bank file.
- _MIDI Monitor_ - Opens a dialog that will display received MIDI messages
- _Fill Screen_ - Hides the menu bar and maximizes the main UI. Can be useful in live playing.
- _Settings_ - Opens a dialog for viewing and editing the contents of the current config file. The program must be restarted for the changes to take effect.

Some program settings, such as the initial height, width, and font size of the UI, can be adjusted by editing the script itself and changing the values of _WIDTH, HEIGHT, FONTSIZE, PAD, FILLSCREEN_ at the beginning of the file.
