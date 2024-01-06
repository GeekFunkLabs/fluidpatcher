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
A list of MIDI messages to send. Individual messages are formatted as `<type>:<channel>:<par1>:<par2>`, where the type can be `note`, `noteoff`, `cc`, `kpress`, `pbend`, `cpress`, or `prog`. The last three types only have one parameter and should omit `par2`.

### `fluidsettings`
A mapping of FluidSynth [settings](http://www.fluidsynth.org/api/fluidsettings.xml) and the values to set. Only settings that begin with `synth` will have any effect while the synth is running - any others should be set in the config file.

### `router_rules`

A list of rules for routing incoming MIDI messages to synthesizer events. Each rule is a mapping with parameters that define what messages should trigger it, as well as how it should modify the events it sends to the synth. Every rule that matches a message is triggered, so a message can trigger multiple events, and rules can't override previous rules. When selecting a patch, default rules are created that pass on all messages unmodified to the synth. A rule that is just the string `clear` will clear all previous router rules, including the defaults.

Like MIDI messages, a router rule must have a `type` parameter, and can also have `chan`, `par1`, and `par2` parameters. A parameter that is not present in a rule will match any value of that parameter.

Valid rule types are `note`, `noteoff`, `cc`, `kpress`, `pbend`, `cpress`, or `prog`, and system realtime messages `clock`, `start`, `stop`, or `continue`. A rule can produce an event of a different type from the triggering event by specifying the type as `<type>=<newtype>`. If the triggering message has a different number of parameters than the new type, the parameters of the new event are determined in specific ways:

* 2-parameter to 1-parameter: `par2` of rule determines `par1` of event
* 1-parameter to 2-parameter: `par1` of rule determines `par2` of event, `par1` of event is *from_min* of `par2`
* 


If the message has two parameters and the new type has only one, the second parameter of the original message is routed to the single parameter of the new message according to `par2`. If routing a one-parameter message to a two-parameter type, the first parameter of the original message is routed to the second parameter of the new message according to `par1`, and the first parameter of the new message is given by `par2`.

The other rule parameters can be specified as `<from_min>-<from_max>=<to_min>-<to_max>`. This scales values in the _from_ range to values in the _to_ range for par1 and par2, and for channels any message on a channel in the _from_ range generates an event on every channel in the _to_ range. The _from_ and _to_ ranges can each be a single number, and the _to_ range can be left out. These parameters can also be specified as `<from_min>-<from_max>*<factor>+<offset>`. Message values in the _from_ range are multiplied by _factor_, then _offset_ is added to them. 

Additional parameters can be added to rules to make them trigger actions or control things, instead of sending events to the synth. A rule with a `fluidsetting` parameter will change the value of a FluidSynth setting to the result of `par1` or `par2` routing, depending on whether the triggering MIDI message is a one- or two-parameter type. Rules with a `patch` parameter can be used to select patches. The value can be a patch index or name, or a number followed by `+` or `-`, which increments the patch number by that amount. A value of `select` sets the patch index to the value of the routed message.

### sequencers
Contains one or more named sequencers that can play a series of looped notes. The name of each item is used to connect router rules to it. A sequencer can have the following attributes:

- `notes`(required) - a list of note messages the sequencer will play. There must be a soundfont preset assigned to the MIDI channel of the notes in order to hear them.
- `tempo` - in beats per minute, defaults to 120
- `tdiv` - the length of the notes in the pattern expressed as the number of notes in a measure of four beats. Defaults to 8
- `swing` - the ratio by which to stretch the duration of on-beat notes and shorten off-beat notes, producing a "swing" feel. Values range from 0.5 (no swing) to 0.99. Default is 0.5
- `groove` - an amount by which to multiply the volume of specific notes in a pattern, in order to create a rhythmic feel. Can be a single number, in which case the multiplier is applied to every other note starting with the first, or a list of values. Default is 1
  
A router rule can control a sequencer if it has a `sequencer` parameter with the sequencer's name as the value. The value of the routed MIDI message controls how many times the sequence will loop. A value of 0 stops the sequencer, and negative values will cause it to loop indefinitely.
  
### arpeggiators
Contains one or more named arpeggiators that will capture any notes routed to them and repeat them in a pattern as long as the notes are held.

- `tempo`, `tdiv`, `swing`, `groove` - same as for sequencers
- `octaves` - number of octaves over which to repeat the pattern. Defaults to 1
- `style` - can be `up`, `down`, `both`, or `chord`. The first three options loop the held notes in ascending sequence, descending, or ascending followed by descending. The `chord` option plays all held notes at once repeatedly. If not given, the notes are looped in the order they were played.
  
To make the arpeggiator work, create a `note` type router rule with an `arpeggiator` parameter that has the arpeggiator's name as its value. There must be a soundfont preset assigned on the MIDI channel to which the notes are routed in order to hear them.
  
### midiplayers
Contains one or more named midiplayers that can play, loop, and seek within MIDI files.

- `file`(required) - the MIDI file to play, can also be a list of files to play in sequence
- `tempo` - tempo at which to play the file, in bpm. If not given, the tempo messages in the file will be obeyed
- `loops` - a list of pairs of _start, end_ ticks. When the song reaches an _end_ tick, it will seek back to the previous _start_ tick in the list. A negative _start_ value rewinds to the beginning of the song and stops playback.
- `barlength` - the number of ticks corresponding to a whole number of musical measures in the song. If the midiplayer is playing and a router rule tells it to seek to a point in the song, it will wait until the end of a bar to do so. By default barlength is 0 and seeking will occur immediately.
- `chan` - a channel routing specification, of the same format as for a router rule, for all the messages in the file. This can be useful if your MIDI controller plays on the same channel as one or more of the tracks in the file, and you don't want the messages to interfere.
- `mask` - a list of MIDI message types to ignore in the file. A useful value is `['prog']`, which will prevent program changes in the file from changing your patch settings.
  
A router rule with a `midiplayer` parameter will tell the named midiplayer to play if the routed message value is positive or pause if the value is zero. If the rule also has a `tick` parameter, the midiplayer will seek to that tick position in the song. If the value of `tick` has a `+` or `-` suffix the midiplayer will seek forward or backward from the current position. If the routed message value is negative and the midiplayer is currently playing, seeking will be postponed until the song reaches the end of a measure as specified by `barlength`.

> The tempo of sequencers, arpeggiators, and midiplayers can be set with a router rule that has a `tempo` 
> parameter with the target's name as its value. For this reason the names of all these units within a bank file 
> should be unique. A router rule with a `sync` parameter will set the tempo of the named unit by measuring the 
> time between successive MIDI messages matching the rule, allowing a user to set the tempo by tapping a button 
> or key. The value of the routed message sets the number of beats to sync to the time interval. These units can 
> also be synchronized with an external device or program that sends a MIDI clock signal by adding a router rule 
> of type `clock` with a `sync` parameter. Note that any tempo changes to a midiplayer will cause it to stop 
> paying attention to any tempo change messages in the file. This behavior can be resumed using by setting a 
> tempo of zero.

### ladspafx
Contains one or more named units that activate and control external LADSPA effect plugins. These must be installed separately and are system-dependent. On Linux, the `listplugins` and `analyseplugin` commands are useful for determining the available plugins and their parameters.

- `lib`(required) - the effect plugin file (_.dll, .so_, etc. depending on system)
- `plugin` - the name of the plugin within the file, required if there's more than one
- `chan` - the channel(s) from which audio should be routed to the effect, as a single value, a `<from_min>-<from_max>` range, or list. This will only have effect if a multichannel-capable audio driver such as _JACK_ is used, otherwise effects will be active on all channels.
- `audio` - `stereo`, `mono`, or a list of the audio input and output ports in the plugin. `stereo` is converted to `['Input L', 'Input R', 'Output L', 'Output R']`, and `mono` to `['Input', 'Output']`. Ports will match the closest unique name, but if the plugin author names their ports differently you can give them explicitly. Default is `stereo`
- `vals` - a mapping of control port names to initial values to set them with
  
Router rules can be used to control effects unit parameters by including a `ladspafx` parameter with the effect unit name, and a `port` parameter with the control port name/nearest match.
