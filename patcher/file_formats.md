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

All settings are optional, and the order is flexible. The Patcher will use the default values shown in curly braces above if the settings aren't given or a config file isn't provided. A full list of fluidsynth settings is at [fluidsynth.org/api/fluidsettings.xml](http://www.fluidsynth.org/api/fluidsettings.xml), any that aren't specified in the config file will be given the default value based on platform. Fluidsynth settings in the config file are applied once, when the synth is first activated.

## Bank Files

A bank file contains one or more patches. A patch sets instrument sounds on one or more MIDI channels, as well as many other settings such as MIDI routing rules, MIDI messages to send when the patch is selected, MIDI files to play, sequence or arpeggiator patterns that can be triggered, and even external LADSPA effects to use. Many of these settings can be set globally for all patches in the bank as well.

Here is an example bank file (explanation below): 
```yaml
patches:
  FM Piano:
    1: FM Piano.sf2:000:000 
  Synth Bass and Piano:
    3: FluidGM_R3.sf2:000:000
    4: VintageDreamsWaves-v2.sf2:000:028
    router_rules:
    - {type: note, chan: 1=4, par1: B4-G9}
    - {type: note, chan: 1=4, par1: C0-Bb4*1-12}
    - type: note
      chan: 1=4
      par1: C0-Bb4*1-12
    messages:
    - cc:3:91:127
    - cc:3:93:127
  Analog Synth:
    1: ModSynth.sf2:000:000
    ladspafx:
      mydelay:
        lib: delay.so
        audio: mono
        vals:
          Delay: 0.3
    router_rules:
    - clear
    - {type: note, chan: 1, par2: 0-127=127}
    - {type: pbend, chan: 1}
    - {type: cc, chan: 1}
    - {type: cc, chan: 1, par1: 15, par2: 0-127=0-2.5, ladspafx: mydelay, port: Delay}
  Jazz Jam:
    2: FM Piano.sf2:000:000
    3: ModSynth:000:007
    4: ModSynth:000:002
    7: JazzCombo.sf2:000:020
    8: JazzCombo.sf2:000:035
    10: JazzCombo.sf2:128:004
    sequencers:
      synthpads:
        tdiv: 1
        notes: [note:3:A5:70, note:3:G5:70, note:3:A5:70, note:3:C6:70]
    arpeggiators:
      moody:
        tdiv: 12
        octaves: 2
    players:
      jazz:
        file: smoothjazz.mid
        chan: 1-2*1+6
        barlength: 1536
        loops: [15360, 18429]
    router_rules:
    - {type: note, chan: 1=2, par1: C4-C9}
    - {type: note, chan: 1, par1: A#2, par2: 1-127=4, sequencer: synthpads}
    - {type: note, chan: 1=3, par1: C3-B3, arpeggiator: moody}
    - {type: note, chan: 1, par1: F2, par2: 1-127=1, player: jazz}
    - {type: note, chan: 1, par1: B2, par2: 1-127=1, player: jazz, tick: 13824}
    - {type: cc, chan: 1, par1: 17, par2: 1-127=0, player: jazz}
    - {type: cc, chan: 1, par1: 15, par2: 0-127=30-240, tempo: jazz}
    - {type: cc, chan: 1, par1: 15, par2: 0-127=30-240, tempo: synthpads}
    - {type: cc, chan: 1, par1: 15, par2: 0-127=30-240, tempo: moody}

router_rules:
- {type: cc, chan: 1=2-16, par1: 7}
- {type: cc, chan: 1, par1: 18, par2: 0-127=0-1, fluidsetting: synth.reverb.room-size}

messages:
- cc:3:91:80
- cc:3:93:80

fluidsettings:
  synth.reverb.level: 0.9
  synth.gain: 0.6

init:
  messages:
  - cc:3:7:80
  - cc:1:73:0
  - cc:1:74:0
```

A bank file must contain a `patches` item. The item names in `patches` will be the patch names in the bank. The other keywords described below can be used in individual patches, or at the zero indent/bank level. When a patch is selected, the bank keywords will be applied first, followed by the keywords in the selected patch. If a bank contains an `init` item, the keywords in `init` will be applied once, when the bank is first loaded (although this only makes sense for `messages` and `fluidsettings` - other keywords are ignored).

Unrecognized keywords in a bank file will usually just be ignored. Anything on a line after a hash symbol (`#`) is considered a comment. Because comments are ignored by YaML, they may be lost if a bank file is modified and saved. A way of preserving comments is to store them in unique keywords, e.g. `comment1`, `comment2` etc.

### Keywords

- `<channel #>` - an integer used as a keyword sets a soundfont preset on that channel, specified with the format `<soundfont file>:<bank>:<preset>`. MIDI channel numbers are numbered starting with channel 1, the way they are on virtually all synthesizers, controllers, DAWs, etc. This is in contrast to FluidSynth, which numbers channels beginning with 0. Patcher handles all of the translation between channel numbering schemes.
- `router_rules` - contains a list of rules for how to route MIDI messages. Each rule is a mapping that both describes what messages it should apply to, and how to modify those messages. If a rule is the string `clear` instead of a mapping it will clear all previous router rules, including the default one-to-one channel, type, and parameter rules. A rule can have the following parameters:
  - `type`(required) - can be `note`, `cc`, `prog`, `pbend`, `kpress`, or `cpress`
  - `chan` - the channel(s) from which to route messages and how to route them. This can be specified in any of the following ways:
    - `<channel #>` - selects the single channel to be affected by this rule
    - `<from_min>-<from_max>` - selects a range of channels
    - `<from_min>-<from_max>=<to_min>-<to_max>` - a message from any channel in the _from_ range is copied to every channel in the _to_ range. Either range can be a single integer
    - `<from_min>-<from_max>*<mul>+<add>` - messages from channels in the specified range have their channel number multiplied by `mul`, then added to `add`. The multiplier can be a decimal, and `add` can be negative
  - `par1` - describes how the first parameter of the MIDI message is routed, using the same formats as for `chan`, except that if the form `<from_min>-<from_max>=<to_min>-<to_max>` is used, values in the _from_ range are scaled to values in the _to_ range
  - `par2` - routes the second parameter of the MIDI message for _note on, note off, control change, and key pressure_ messages
  - `type2` - changes the `type` of the MIDI message. If the message has two parameters and the new type has only one, the second parameter of the original message is routed to the single parameter of the new message according to `par2`. If routing a one-parameter message to a two-parameter type, the first parameter of the original message is routed to the second parameter of the new message according to `par1`, and the first parameter of the new message is given by `par2`.

  Additional rule parameters can be specified to trigger actions or control things. In this case the message will be given a value attribute that is the result of `par1` or `par2` routing, depending on whether the MIDI event has one or two parameters.
  - `fluidsetting` - a FluidSynth setting to change when a matching MIDI message is received.
  - `sequencer|arpeggiator|player|tempo|ladspafx` - these are used to control MIDI players and external LADSPA effects, described below
  
  Any other additional parameter(s) in the rule will be sent to a callback function. An implementation can then use these actions to trigger its own events (e.g. changing patches, loading banks, etc.). See the [Patcher API description](README.md) for details.

- `messages` - a list of MIDI messages to send. The format is `<type>:<channel>:<par1>:<par2>`, where the _type_ is `note`, `noteoff`, `cc`, `pbend`, `cpress`, `kpress`, `prog`, or `sysex`. One-parameter messages can omit `par2`. For `sysex` messages a _destination_ is given instead of a channel, and the SysEx bytes are sent to the closest-matching MIDI port name, or FluidSynth itself if the destination matches or is an empty string. The remaining tokens can be a _.syx_ file to read from, or a `:`-separated list of the SysEx message bytes, as decimal or hex.

- `fluidsettings` - a mapping of FluidSynth [settings](http://www.fluidsynth.org/api/fluidsettings.xml) and the values to set. Some settings, such as those for the audio driver, can only be applied when the synth is created and will have no effect in bank files.

- `sequencers` - a mapping that creates one or more sequencers that can play a series of looped notes. The name of each item is used to connect router rules to it. A sequencer can have the following attributes:
  - `notes`(required) - a list of note messages the sequencer will play. There must be a soundfont preset assigned to the MIDI channel of the notes in order to hear them.
  - `tdiv` - the number of notes per measure, assuming a 4/4 time signature. Defaults to 8
  - `swing` - the ratio by which to stretch the duration of on-beat notes and shorten off-beat notes, producing a "swing" feel. Values range from 0.5 (no swing) to 0.99 (Benny Goodman). Default is 0.5
  - `tempo` - in beats per minute, defaults to 120
  
  A router rule can control a sequencer if it has a `sequencer` parameter with the sequencer's name as the value. The value of the routed MIDI message controls how many times the sequence will loop. A value of 0 stops the sequencer, and negative values will cause it to loop indefinitely.
  
- `arpeggiators` - a mapping of special sequencers that will record any notes routed to them and repeat them in a pattern as long as the notes are held.
  - `tdiv` - notes per measure, assuming 4/4 time
  - `swing` - same as for sequencers
  - `tempo` - beats per minute
  - `octaves` - number of octaves over which to repeat the pattern
  - `style` - can be `up`, `down`, or `both`. Plays the notes in ascending sequence, descending, or ascending followed by descending. If not given, the notes are played in the order received.
  
  To make the arpeggiator work, create a `note` type router rule with an `arpeggiator` parameter that has the arpeggiator's name as its value. There must a soundfont preset assigned on the MIDI channel to which the notes are routed in order to hear them.
  
- `players` - a mapping of player units that can play, loop, and seek within MIDI files.
  - `file`(required) - the MIDI file to play
  - `chan` - a channel routing specification, of the same format as for a router rule, for all the messages in the file. This can be useful if your MIDI controller plays on the same channel as one or more of the tracks in the file, and you don't want the messages to interfere.
  - `filter` - a list of message types to ignore in the file. By default this is `['prog']`, so you can set the instruments for each channel played in the song without them being altered by program changes in the file. To use general MIDI instruments, you can instead set this to `[]` and set a preset from a GM font on the first channel, and FluidSynth will in most cases select the appropriate instruments.
  - `loops` - a list of pairs of _start, end_ ticks. When the song reaches an _end_ tick, it will seek back to the previous _start_ tick in the list.
  - `barlength` - the number of ticks corresponding to a whole number of musical measures in the song. If the player is playing and a router rule tells it to seek to a point in the song, it will wait until the end of a bar to do so. By default barlength is 0 and seeking will occur immediately.
  - `tempo` - tempo at which to play the file, in bpm. If not given, the tempo messages in the file will be obeyed
  
  A router rule with a `player` parameter will tell the named player to start if its value is >0, or stop otherwise. If the rule also has a `tick` parameter, the player will seek to that tick value, possibly waiting until the end of a bar as described above.
  
  The tempo of a sequencer, arpeggiator, or player can be set with a router rule that has a `tempo` parameter with the target's name as its value. The names of sequencers, arpeggiators, and players should all be unique.

- `ladspafx` - a mapping of external [LADSPA](https://github.com/FluidSynth/fluidsynth/blob/master/doc/ladspa.md) effects units to activate. These must be installed separately and are system-dependent. On Linux, the `listplugins` and `analyseplugin` commands are useful for determining the available plugins and their parameters.
  - `lib`(required) - the effect plugin file (_.dll, .so_, etc. depending on system)
  - `plugin` - the name of the plugin within the file, required if there's more than one
  - `chan` - the channel(s) from which audio should be routed to the effect, as a single value, a `<from_min>-<from_max>` range, or list. This will only have effect if a multichannel-capable audio driver such as _JACK_ is used, otherwise effects will be active on all channels.
  - `audio` - `stereo`, `mono`, or a list of the audio input and output ports in the plugin. `stereo` is converted to `['Input L', 'Input R', 'Output L', 'Output R']`, and `mono` to `['Input', 'Output']`. Ports will match the closest unique name, but if the plugin author names their ports differently you can give them explicitly. Default is `stereo`
  - `vals` - a mapping of control port names to initial values to set them with
  
  Router rules can be used to control effects unit parameters by including a `ladspafx` parameter with the effect unit name, and a `port` parameter with the control port name/nearest match.