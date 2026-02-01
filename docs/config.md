# Configuration

## Location

FluidPatcher keeps a small YAML config file that is used to specify file
locations, FluidSynth settings, and to store program states. By default, 
configuration lives at:

```
~/.config/fluidpatcher/fluidpatcherconf.yaml
```

You may override the location entirely using the environment variable:

```
export FLUIDPATCHER_CONFIG=/path/to/myconfig.yaml
```

# Format

If not found, FluidPatcher creates a default config file like the one
below:

```yaml
banks_path: ~/.config/fluidpatcher/banks
sounds_path: ~/.config/fluidpatcher/sounds
midi_path: ~/.config/fluidpatcher/midi
ladspa_path: /usr/lib/ladspa
fluidsettings:
  midi.autoconnect: 1
  player.reset-synth: 0
  synth.ladspa.active: 1
  synth.audio-groups: 16
```

The keys `banks_path`, `sounds_path`, `midi_path`, and `ladspa_path`
specify locations for these file types. Fluidpatcher will expand file
names using these paths, allowing short filenames to be used in banks
and enhancing portability. Absolute paths can be used to override
the config paths when desired.

The `fluidsynth` section contains key/value pairs for
[FluidSynth settings](https://www.fluidsynth.org/api/fluidsettings.xml).
FluidSynth will work with the default values on most platforms, but a
few useful settings are:

* `midi.autoconnect` -  If 1 (TRUE), automatically connects FluidSynth
    to available MIDI input ports. alsa_seq, coremidi and jack are
    currently the only drivers making use of this.
* `player.reset-synth` - When playing a MIDI file and reaching the end
    of a song, all playing notes will be silenced and the synth reset,
    overriding settings in banks and patches. This is undesirable for
    FluidPatcher and should be set to 0.
* `synth.gain` - scales the output volume of the synth. This can be in
    the range 0.0-10.0, but values above 1.0 will be clipped/distorted.
* `synth.polyphony` - If too many voices are played at once (usually by
    sustaining lots of notes), the CPU may terminate audio while it
    catches up. This limits the number of active voices, canceling the
    oldest notes.
* `audio.driver`, `audio.<driver>.device` - Allows setting the audio
    driver and device, if the default doesn't work
* `audio.periods`, `audio.period-size` - These set the number and size
    of the buffers used for sending digital audio. Lowering these values
    decreases audio latency (the time between playing a note and hearing
    the audio), but too low and the sound card won't be able to keep up,
    producing stuttering/crackling audio.


## Resetting configuration

Delete the config file and directories:

```bash
rm -rf ~/.config/fluidpatcher
```

Next run will regenerate defaults.

