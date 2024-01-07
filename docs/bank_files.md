# Bank Files

Bank files are [YAML](https://yaml.org/)-formatted text files that control many FluidSynth settings, from the soundfont presets that are selected for each MIDI channel to the way that MIDI messages from a controller interact with those presets. They can also activate and control tools such as MIDI file players, sequencers, arpeggiators, and LADSPA effect plugins.

YAML is a plain text format that stores data, either as lists or as mappings (sets of `<key>: <value>` pairs). Lists and mappings can be nested within each other, and nesting level is indicated by indenting at least two spaces per level. List elements are placed on separate lines and preceded by a dash, or can be written on a single line as a comma-separated list enclosed in square brackets. Mapping items are listed on separate lines, or on a single line as a comma-separated list enclosed in curly braces.

Geek Funk Labs has produced a [series of lesson videos](https://youtube.com/playlist?list=PL4a8Oe3qfS_-CefZFNYssT1kHdzEOdAlD) that teach about creating bank files and the many features of FluidSynth, SoundFonts, and MIDI.

## Structure

Bank files have three main sections:

* A `patches` section that contains the individual patches
* An `init` section that is read when the bank is loaded
* The zero-indent or bank level - everything that is outside the other two sections

When a patch is selected, bank settings are applied first, followed by the patch settings. The settings in `init` are read before bank and patch settings once, when the bank is loaded. Settings are applied in the order listed in each section. For example, when selecting the `Harpsichord` patch in the bank shown below, `synth.reverb.room-size` is first set to 0.6 by the bank-level `fluidsettings`, then set to 0.1 in the patch.

```yaml
init:
  messages: [cc:1:91:100, cc:2:91:20]
patches:
  Harpsichord:
    1: defaultGM:sf2:000:006
    fluidsettings:
      synth.reverb.room-size: 0.1
  Piano and Bass:
    2: defaultGM.sf2:000:000
    3: defaultGM.sf2:000:034
router_rules:
  - {type: note, chan: 1=2, par1: C1-B3}
  - {type: note, chan: 1=3, par1: C4-B6}
fluidsettings:
  synth.reverb.room-size: 0.6
```

Each section can contain any of the keywords described below, although in the `init` section only `messages` and `fluidsettings` make sense - others will be ignored. The bank files included with the repository in `scripts/config/banks` provide additional examples.

## Keywords

### `<number>`

A number as a keyword indicates a MIDI channel on which a preset is to be selected. The preset is specified with the form `<soundfont file>:<bank>:<preset>`. MIDI channel numbers in bank files are numbered starting with channel 1.

### `messages`
A list of MIDI messages to send. The format depends on message type:

* Types `note`, `noteoff`, `kpress`, `cc` have two parameters - note number and velocity or controller number and value - and use format `<type>:<channel>:<par1>:<par2>`. The second parameter can be a number or note name (e.g. C#4).
* One-parameter messages `pbend`, `cpress`, `prog` use format `<type>:<channel>:<par1>:`
* System realtime messages `clock`, `start`, `continue`, `stop` have no parameters or channel, and use format `<type>:::`

### `fluidsettings`

A mapping of FluidSynth [settings](http://www.fluidsynth.org/api/fluidsettings.xml) and the values to set. Only settings that begin with `synth` will have any effect while the synth is running - any others should be set in the config file.

### `router_rules`

A list of rules for routing incoming MIDI messages - from MIDI controllers, the `messages` keyword, or playing MIDI files - to synthesizer events. Rules must have a `type` parameter, and can also have `chan`, `par1`, and `par2` parameters. The values of the parameters define which messages should trigger the rule and how to modify the parameters in the event that is sent to the synth. Every rule that matches a message is triggered, so a message can trigger multiple events and rules can't override previous rules. When selecting a patch, default rules are created that pass on all messages unmodified to the synth. The rule `clear` will erase these and any previous rules.

The `chan`, `par1`, and `par2` parameters can have the following formats:

* a single value matches exactly that value and passes it unmodified
* a range `<from_min>-<from_max>` matches any values in the range without changing them
* `<from_min>-<from_max>=<value>` matches values in the range and sets them to _value_ in the created event
* `<from_min>-<from_max>=<to_min>-<to_max>` matches values in the _from_ range and scales them to values in the _to_ range for `par1` and `par2`; for `chan` a message on a channel in the _from_ range triggers events on every channel in the _to_ range
* `<from_channel>=<min_channel>-<max_channel>` matches messages from the specified channel and creates events on every channel in the given range
* `<from_min>-<from_max>*<factor>+<offset>` matches values in the range, multiplies them by _factor_ and adds _offset_.

The rule type can be any of those listed above in `messages`. The created event can also be a different type from the triggering message by specifying the type as `<type>=<newtype>`. If the new type has a different number of parameters than the triggering message, the parameters of the event are determined as follows:

* 2- to 1-parameter: `par2` becomes `par1`
* 1- to 2-parameter: `par1` becomes `par2`, `par1` is taken from `par2` of the rule
* sytem realtime to 1- or 2-parameter: `chan`, `par1`, and `par2` are set by the rule parameters

Rules can have other parameters, in which case they do not send events to the synth and are used to trigger additional features. A rule with a `fluidsetting` parameter will change the corresponding FluidSynth setting. Rules with a `patch` parameter can be used to select patches - a patch number or name as the parameter value selects that patch, a number followed by `+` or `-` increments the patch number, and `select` sets the patch number according to the message. Patch numbers begin with 1. Other special rules are explained in relevant sections below.

### `midiplayers`

A subsection that contains one or more named midiplayers that can play, loop, and seek within MIDI files.

* `file`(required) - the MIDI file to play
* `tempo` - tempo at which to play the file, in bpm. If not given, the tempo messages in the file will be obeyed
* `loops` - a list of pairs of _start, end_ ticks. When the song reaches an _end_ tick, it will seek back to the previous _start_ tick in the list. If the _start_ tick is a negative number the player stops.
* `barlength` - the number of ticks corresponding to a whole number of musical measures in the song
* `chan` - same format as for a router rule parameter, can route MIDI messages in the file to different channels
* `mask` - a list of MIDI message types to ignore in the file

Router rules for controlling midiplayers have a `midiplayer` parameter with the player name as its value. The file pauses playing if the routed message value is zero, otherwise it plays/resumes. If the rule also has a `tick` parameter, the midiplayer will seek to that tick position in the song. If the value of `tick` has a `+` or `-` suffix the midiplayer will seek forward or backward from the current position. If the routed message value is negative and the midiplayer is currently playing, seeking will be postponed until the song reaches the end of a measure as specified by `barlength`.

A rule with a `tempo` parameter and a midiplayer's name as its value will set the playing tempo of the midiplayer. A router rule with a `sync` parameter will set the tempo of the midiplayer by measuring the time between successive MIDI messages matching the rule, allowing a user to set the tempo by tapping a button or key. The value of the routed message sets the number of beats to sync to the time interval. A `sync` rule with type `clock` will synchronize the player with an external device or program that sends MIDI clock signals. Tempo changes to a midiplayer will cause it to stop paying attention to any tempo change messages in the file. This can be canceled by setting the tempo to zero.

### `sequencers`

A subsection containing one or more named sequencers that can play a series of looped notes. A sequencer can have the following attributes:

* `notes`(required) - a list of note messages the sequencer will play. There must be a soundfont preset assigned to the MIDI channel of the notes in order to hear them.
* `tempo` - in beats per minute, defaults to 120
* `tdiv` - the length of the notes in the pattern expressed as the number of notes in a measure of four beats. Defaults to 8
* `swing` - the ratio by which to stretch the duration of on-beat notes and shorten off-beat notes, producing a "swing" feel. Values range from 0.5 (no swing) to 0.99. Default is 0.5
* `groove` - an amount by which to multiply the volume of specific notes in a pattern, in order to create a rhythmic feel. Can be a single number, in which case the multiplier is applied to every other note starting with the first, or a list of values. Default is 1
  
A router rule with a `sequencer` parameter and the sequencer's name as the value controls the playing of the sequencer. The value of the routed MIDI message controls how many times the sequence will loop. A value of 0 stops the sequencer, and negative values will cause it to loop indefinitely. A rule with a `swing` or `groove` parameter with the sequencer's name will adjust the corresponding sequencer values. Sequencers also respond to `tempo` and `sync` rules in the same way as midiplayers.
  
### `arpeggiators`

This subsection contains one or more named arpeggiators that capture any notes and repeat them in a pattern as long as the notes are held.

* `tempo`, `tdiv`, `swing`, `groove` - same as for sequencers
* `octaves` - number of octaves over which to repeat the pattern. Defaults to 1
* `style` - can be `up`, `down`, `both`, or `chord`. The first three options loop the held notes in ascending sequence, descending, or ascending followed by descending. The `chord` option plays all held notes at once repeatedly. If not given, the notes are looped in the order they were played.
  
To make the arpeggiator work, create a `note` type router rule with an `arpeggiator` parameter that has the arpeggiator's name as its value. There must be a soundfont preset assigned on the MIDI channel to which the notes are routed in order to hear them. Like sequencers, arpeggiators can also be modified by `swing`, `groove`, `tempo`, and `sync` rules.

### `ladspafx`
Contains one or more named units that activate and control external LADSPA effect plugins. See the [Plugins](ladspa_plugins.md) section for details.

* `lib`(required) - the effect plugin file
* `plugin` - the name of the plugin within the file, required if there's more than one
* `group` - a list of audio group numbers on which to send the effects
* `audio` - a list of the audio input and output ports in the plugin
* `vals` - a mapping of control port names and initial values

Router rules can be used to control plugin parameters by providing a `ladspafx` parameter with the effect unit name, and a `port` parameter with the control port name.
