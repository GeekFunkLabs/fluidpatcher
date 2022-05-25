# File Formats


FluidPatcher uses [config files](#config-files) and [bank files](#bank-files) to store the user's preferences and settings. Bank files describe patches - the groups of sound settings a user can switch between while playing - plus rules that describe how MIDI messages are routed, effects settings, etc. Config files contain platform-specific settings, such as the location of bank files and soundfonts and what audio devices to use, allowing bank files to be portable to different systems by simply modifying the config file.

Bank and config files use [YaML](https://yaml.org/) format. Very briefly, YaML is a plain text format that stores data, either as lists or as mappings (sets of `<key>: <value>` pairs). Lists and mappings can be nested within each other, and nesting level is indicated by indenting at least two spaces per level. List elements are placed on separate lines and preceded by a dash, or can be written in compact form as a comma-separated list enclosed in square brackets. Mappings can have their _key: value_ pairs on separate lines, or in a comma-separated list enclosed in curly braces.

## Config Files

Config files have the following structure:

```yaml
soundfontdir: <root path where soundfonts are stored {sf2}>
bankdir: <root path where bank files are stored {banks}>
mfilesdir: <location of MIDI and SYSEX files {''}>
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
- `synth.audio.channels` and `synth.audio.groups` - sets the number of audio output channels. Only useful if you want to route MIDI channels to different effects using the `jack` driver.
- `audio.jack.multi` - set to 1 to enable mult-channel output using `jack`
- `synth.gain` - scales the output volume of the synth. This can be in the range 0.0-10.0, but values above 1.0 will be clipped/distorted.

## Bank Files

A bank file contains one or more patches. A patch selects soundfont presets on one or more MIDI channels, and can also define MIDI routing rules, send MIDI messages, create sequencers, arpeggiators, and MIDI file players, and even activate and control external LADSPA effects. The linked example bank files and definitions below explain the structure and various keywords that are recognized.

This video series teaches about creating bank files and the many features of FluidSynth, SoundFonts, and MIDI:

[![FluidPatcher Lesson Video Series](/assets/fplessons.png)](https://youtube.com/playlist?list=PL4a8Oe3qfS_-CefZFNYssT1kHdzEOdAlD)

### Example Bank Files

These are the example bank files included in this repository. The **parsed** links can be used to show how the bank contents are interpreted as data structures.

[bank0.yaml](/SquishBox/banks/bank0.yaml) ([parsed data](https://codebeautify.org/yaml-parser-online?url=https://raw.githubusercontent.com/albedozero/fluidpatcher/master/SquishBox/banks/bank0.yaml)) - a demo bank that shows off all the bank file keywords/features

[bank1.yaml](/SquishBox/banks/bank1.yaml) ([parsed data](https://codebeautify.org/yaml-parser-online?url=https://raw.githubusercontent.com/albedozero/fluidpatcher/master/SquishBox/banks/bank1.yaml)) - the default bank file, designed with the goal of being useful in the largest range of performance situations

### Structure

A bank file must contain a `patches` item. The item names in `patches` will be the patch names in the bank. The other keywords described below can be used in individual patches, or at the zero indent/bank level. When a patch is selected, the bank keywords will be applied first, followed by the keywords in the selected patch. If a bank contains an `init` item, the keywords in `init` will be applied once, when the bank is first loaded (although this only makes sense for `messages` and `fluidsettings` - other keywords are ignored).

Unrecognized keywords in a bank file will usually just be ignored. Anything on a line after a hash symbol (`#`) is considered a comment. Because comments are ignored by YaML, they may be lost if a bank file is modified and saved. A way of preserving comments is to store them in unique keywords, e.g. `comment1`, `comment2` etc.

### Keywords

- `<channel #>` - an integer used as a keyword sets a soundfont preset on that channel, specified with the format `<soundfont file>:<bank>:<preset>`. MIDI channel numbers are numbered starting with channel 1, the way they are on virtually all synthesizers, controllers, DAWs, etc. This is in contrast to FluidSynth, which numbers channels beginning with 0. Patcher handles all of the translation between channel numbering schemes.

- `router_rules` - contains a list of rules for how to route MIDI messages. An incoming MIDI event is compared to all router rules, and for each rule that matches, an event is created that is modified according to the rule and sent on to the synth. By default, FluidSynth creates one-to-one routing rules for all channels, event types, and parameters. If an item in `router_rules` is the string `clear` it will clear all previous router rules, including the default rules. A rule can have the following parameters:
  - `type`(required) - can be `note`, `cc`, `prog`, `pbend`, `kpress`, `cpress`, or `noteoff`
  - `chan` - the channel(s) from which to route messages and how to route them. This can be specified in any of the following ways:
    - `<channel #>` - selects the single channel to be affected by this rule
    - `<from_min>-<from_max>` - selects a range of channels
    - `<from_min>-<from_max>=<to_min>-<to_max>` - a message from any channel in the _from_ range is copied to every channel in the _to_ range. Either range can be a single integer
    - `<from_min>-<from_max>*<mul>+<add>` - messages from channels in the specified range have their channel number multiplied by `mul`, then added to `add`. The multiplier can be a decimal, and `add` can be negative
  - `par1` - describes how the first parameter of the MIDI message is routed, using the same formats as for `chan`, except that if the form `<from_min>-<from_max>=<to_min>-<to_max>` is used, values in the _from_ range are **scaled** to values in the _to_ range
  - `par2` - routes the second parameter of the MIDI message for _note on, note off, control change, and key pressure_ messages
  - `type2` - changes the `type` of the MIDI message. If the message has two parameters and the new type has only one, the second parameter of the original message is routed to the single parameter of the new message according to `par2`. If routing a one-parameter message to a two-parameter type, the first parameter of the original message is routed to the second parameter of the new message according to `par1`, and the first parameter of the new message is given by `par2`.

  Additional rule parameters can be specified to trigger actions or control things. In this case the message will be given a `val` attribute that is the result of `par1` or `par2` routing, depending on whether the MIDI event has one or two parameters.
  - `fluidsetting` - a FluidSynth setting to change when a matching MIDI message is received.
  - `sequencer|arpeggiator|player|tempo|ladspafx` - these are used to control MIDI players and external LADSPA effects, described below
  
  If the rule has other parameters than these, a callback function will be called with the parameters of the rule and the matching MIDI message. An implementation can use these to trigger its own events. An example of this is the `patch` parameter, which the squishbox.py, headlesspi.py, and fluidpatcher.pyw implementations will use to change patches. If the value of `patch` is a number, the patch number will be incremented by that amount. If the value is `select`, then the value sent by the MIDI message is used to select the patch.

- `messages` - a list of MIDI messages to send. The format is `<type>:<channel>:<par1>:<par2>`, where the _type_ is `note`, `noteoff`, `cc`, `pbend`, `cpress`, `kpress`, `prog`, or `sysex`. One-parameter messages can omit `par2`. For `sysex` messages a _destination_ is given instead of a channel, and the SysEx bytes are sent to the closest-matching MIDI port name, or FluidSynth itself if the destination matches or is an empty string. The remaining tokens can be a _.syx_ file to read from, or a `:`-separated list of the SysEx message bytes, as decimal or hex.

- `fluidsettings` - a mapping of FluidSynth [settings](http://www.fluidsynth.org/api/fluidsettings.xml) and the values to set. Some settings, such as those for the audio driver, can only be applied when the synth is created and will have no effect in bank files.

- `sequencers` - a mapping that creates one or more sequencers that can play a series of looped notes. The name of each item is used to connect router rules to it. A sequencer can have the following attributes:
  - `notes`(required) - a list of note messages the sequencer will play. There must be a soundfont preset assigned to the MIDI channel of the notes in order to hear them.
  - `tdiv` - the number of notes per measure, assuming a 4/4 time signature. Defaults to 8
  - `swing` - the ratio by which to stretch the duration of on-beat notes and shorten off-beat notes, producing a "swing" feel. Values range from 0.5 (no swing) to 0.99. Default is 0.5
  - `groove` - an amount by which to multiply the volume of specific notes in a pattern, in order to create a rhythmic feel. Can be a single number, in which case the multiplier is applied to every other note starting with the first, or a list of values.
  - `tempo` - in beats per minute, defaults to 120
  
  A router rule can control a sequencer if it has a `sequencer` parameter with the sequencer's name as the value. The value of the routed MIDI message controls how many times the sequence will loop. A value of 0 stops the sequencer, and negative values will cause it to loop indefinitely.
  
- `arpeggiators` - a mapping of special sequencers that will capture any notes routed to them and repeat them in a pattern as long as the notes are held.
  - `tdiv`, `swing`, `groove`, `tempo` - same as for sequencers
  - `octaves` - number of octaves over which to repeat the pattern. defaults to 1
  - `style` - can be `up`, `down`, `both`, or `chord`. The first three loops the held notes in ascending sequence, descending, or ascending followed by descending. The `chord` option plays all held notes at once repeatedly. If not given, the notes are looped in the order they were played.
  
  To make the arpeggiator work, create a `note` type router rule with an `arpeggiator` parameter that has the arpeggiator's name as its value. There must be a soundfont preset assigned on the MIDI channel to which the notes are routed in order to hear them.
  
- `players` - a mapping of player units that can play, loop, and seek within MIDI files.
  - `file`(required) - the MIDI file to play, can also be a list of files to play in sequence
  - `chan` - a channel routing specification, of the same format as for a router rule, for all the messages in the file. This can be useful if your MIDI controller plays on the same channel as one or more of the tracks in the file, and you don't want the messages to interfere.
  - `mask` - a list of MIDI message types to ignore in the file. By default this is `['prog']`, so that program changes in the file won't affect the instrument settings in your patch.
  - `loops` - a list of pairs of _start, end_ ticks. When the song reaches an _end_ tick, it will seek back to the previous _start_ tick in the list. A loop _end_ with a negative value refers to ticks starting from the end of the song and going backward. A negative _start_ value rewinds to the beginning of the song and stops playback.
  - `barlength` - the number of ticks corresponding to a whole number of musical measures in the song. If the player is playing and a router rule tells it to seek to a point in the song, it will wait until the end of a bar to do so. By default barlength is 0 and seeking will occur immediately.
  - `tempo` - tempo at which to play the file, in bpm. If not given, the tempo messages in the file will be obeyed
  
  A router rule with a `player` parameter will tell the named player to play if its value is >0, or stop otherwise. If the rule also has a `tick` parameter, the player will seek to that tick value, possibly waiting until the end of a bar as described above.
  
  The tempo of a sequencer, arpeggiator, or player can be set with a router rule that has a `tempo` parameter with the target's name as its value. The names of sequencers, arpeggiators, and players should all be unique.

- `ladspafx` - a mapping of external [LADSPA](https://github.com/FluidSynth/fluidsynth/blob/master/doc/ladspa.md) effects units to activate. These must be installed separately and are system-dependent. On Linux, the `listplugins` and `analyseplugin` commands are useful for determining the available plugins and their parameters.
  - `lib`(required) - the effect plugin file (_.dll, .so_, etc. depending on system)
  - `plugin` - the name of the plugin within the file, required if there's more than one
  - `chan` - the channel(s) from which audio should be routed to the effect, as a single value, a `<from_min>-<from_max>` range, or list. This will only have effect if a multichannel-capable audio driver such as _JACK_ is used, otherwise effects will be active on all channels.
  - `audio` - `stereo`, `mono`, or a list of the audio input and output ports in the plugin. `stereo` is converted to `['Input L', 'Input R', 'Output L', 'Output R']`, and `mono` to `['Input', 'Output']`. Ports will match the closest unique name, but if the plugin author names their ports differently you can give them explicitly. Default is `stereo`
  - `vals` - a mapping of control port names to initial values to set them with
  
  Router rules can be used to control effects unit parameters by including a `ladspafx` parameter with the effect unit name, and a `port` parameter with the control port name/nearest match.
