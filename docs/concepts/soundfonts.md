# SoundFonts

SoundFont files (`.sf2`) contain audio samples and synthesis parameters
used to reproduce musical instruments. Software and hardware that
follow the [SoundFont specification](http://www.synthfont.com/sfspec24.pdf)
can render the same SoundFont in a consistent and portable way.

## Terminology

Common SoundFont terms used throughout the documentation:

Preset
: A single playable instrument defined by the soundfont.

Bank
: A collection of up to 128 presets. Banks are numbered from `0–16383`.

Program
: The index of a preset within a bank (`0–127`).

Generator
: A synthesis parameter controlling how samples are played
  (e.g. filter cutoff, envelope times).

Modulator
: A rule that connects MIDI messages to generators.

## Selecting presets

In a bank file, an integer key at the root or patch level selects the
preset assigned to that MIDI channel.

Presets are specified using the format:

```yaml
<soundfont file>:<bank>:<program>
```

For example:

```yaml
1: piano.sf2:0:0
```

Channel assignments at the patch level override those defined at the
root. When a patch is applied, any channel without an assigned preset
is explicitly unset, meaning no sound will be produced on that channel.

## Modulators and control

The SoundFont specification defines a set of default modulators
(e.g. modulation wheel, channel volume, reverb send) that respond to
standard MIDI Control Change (CC) messages. FluidSynth implements most
of these defaults; see the FluidSynth
[control change implementation chart](https://github.com/FluidSynth/fluidsynth/wiki/FluidFeatures#midi-control-change-implementation-chart)
for details.

FluidPatcher does not expose a direct API for creating or modifying
SoundFont modulators at runtime. However:

* **NRPN messages** can be used to access all SoundFont generators,
  as defined by the specification.
* **Custom modulators** can be authored directly in the SoundFont file
  using editors such as [PolyPhone](https://www.polyphone.io).

The `ModSynth_R1.sf2` SoundFont included with this repository
demonstrates custom modulators defined within the SoundFont itself.

