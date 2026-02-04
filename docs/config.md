# Configuration

FluidPatcher keeps its global configuration in a YAML file, created
automatically on first run.

## Location

By default, the config file is stored at:

```
~/.config/fluidpatcher/fluidpatcherconf.yaml
```

You can override this location by setting the `FLUIDPATCHER_CONFIG`
environment variable:

```shell
export FLUIDPATCHER_CONFIG=/path/to/myconfig.yaml
```

If the file does not exist, fluidpatcher will:

1. Create the directory
2. Copy in a bundled default configuration
3. Populate default folders if they’re missing

FluidPatcher will work on most platforms without editing this file,
but it's safe to do so.

## Format

At runtime, the configuration is loaded into a single mapping called
`CONFIG`. Most values are paths and global settings rather than musical
behavior.

Key entries include:

| Key             | Meaning                                          |
| --------------- | ------------------------------------------------ |
| `banks_path`    | Directory containing your `.yaml` bank files     |
| `sounds_path`   | Where SoundFont (`.sf2`) files live              |
| `midi_path`     | Default location for MIDI files                  |
| `ladspa_path`   | Where LADSPA plugins are searched for            |
| `fluidsettings` | Raw FluidSynth settings passed through unchanged |

FluidPatcher will expand file names using these paths, allowing short
filenames to be used in banks and enhancing portability. Absolute paths
can be used to override the config paths when desired.

If you omit `banks_path`, `sounds_path`, or `midi_path`, FluidPatcher
fills in sensible defaults relative to the config file.

## FluidSynth Settings

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

## Resetting Configuration

Delete the config file and directories:

```bash
rm -rf ~/.config/fluidpatcher
```

Next run will regenerate defaults.

