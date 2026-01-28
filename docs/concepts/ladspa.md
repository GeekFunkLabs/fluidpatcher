# Effects (LADSPA)

FluidSynth can natively host **LADSPA** plugins to apply audio effects
such as amplification, filtering, delay, and reverb. LADSPA plugins
operate at the audio level, after MIDI events have been rendered to
sound.

FluidPatcher builds on this capability by allowing banks to define
effect chains, route audio to them on a per-channel basis, and control
effect parameters using MIDI rules.

At present, LADSPA support is provided on Linux systems. While LADSPA
plugins can be built on other platforms, FluidPatcher does not
currently support or test non-Linux configurations.

## FluidSynth Audio Routing

FluidSynth provides a flexible—though correspondingly complex—audio
routing graph. FluidPatcher abstracts most of this away, but
understanding the basics is helpful when working with effects.

Audio is rendered into one or more **audio groups**. These groups are
the units that can be routed through LADSPA effect chains. The number
of available groups is set using the fluidsetting `synth.audio-groups`.

Audio from MIDI channels is assigned to audio groups sequentially. If
there are fewer groups than channels, the assignment wraps around. For
example, with `synth.audio-groups: 4` and 16 MIDI channels:

* Group 1 receives audio from channels 1, 5, 9, 13
* Group 2 receives audio from channels 2, 6, 10, 14
* and so on

For maximum routing flexibility, the number of audio groups can be set
equal to the number of MIDI channels. This increases CPU usage, since
separate effect instances are created internally for each group. If
performance is a concern, reducing the number of groups can
significantly lower overhead.

## Enabling LADSPA Support

The following configuration settings enable LADSPA processing:

```yaml
ladspa_path: /usr/lib/ladspa
fluidsettings:
  synth.audio-groups: 16
  synth.ladspa.active: 1
```

FluidSynth can output multiple stereo pairs (`synth.audio-channels`).
As a result, audio groups processed by effects are not mixed back to
the main output by default.

To address this, FluidPatcher includes a lightweight LADSPA plugin,
`patchcord.so`, which is automatically appended to the end of an effect
chain to mix audio groups back together.

Prebuilt versions of `patchcord` are included for several platforms.
If a prebuilt binary is unavailable, `pip` can compile the plugin from
the included source, provided the LADSPA SDK is installed. On
Debian-based systems, the SDK can be installed with:

```bash
sudo apt install ladspa-sdk
```

## Defining Effects in Bank Files

Effects are defined using the `ladspafx` section at the root or patch
level of a bank file. Each entry represents a single effect instance
and is identified by a user-defined name.

Audio is routed through plugins in the order they are declared:
root-level plugins first, followed by patch-level plugins. If applying
a patch changes the effect chain, FluidPatcher must tear down and
rebuild the chain, which may briefly interrupt audio. To avoid this,
effects can be defined exclusively at the bank’s root level.

### `ladspafx`

Each effect unit supports the following parameters:

* **`lib`** *(required)*
  The LADSPA plugin file name (without path)

* **`plugin`**
  The plugin label within the file
  Required if the file contains multiple plugins

* **`audio`**
  A list of audio port names, with inputs listed first and outputs last
  Partial names may be used if they uniquely identify a port
  The aliases `mono` and `stereo` correspond to the layouts
  `Input, Output` and `Input L, Input R, Output L, Output R`

* **`vals`**
  A mapping of control port names to their initial values

* **`chan`**
  A single MIDI channel or list of channels whose audio is routed
  through the plugin

Effects defined at the patch level override effects defined at the
root level.

### Rule-Driven Effect Control

MIDI rules can modify effect parameters by including an
`fx: [ladspafx name]>[port name]` parameter.

When a rule matches a MIDI message, the transformed value of that
message is applied to the specified control port. This allows
controllers, envelopes, sequences, and other rule-driven events to
dynamically shape effects during performance.

## Plugin Inspection

Configuring an effect requires knowing the plugin’s audio and
control ports. This information is not inferred automatically.

The LADSPA SDK provides the `listplugins` and `analyseplugin`
utilities, which list available plugins and print detailed information
about a specific plugin’s ports. This output is the authoritative
reference for:

* Plugin labels
* Audio input and output port names
* Control port names, ranges, and default values

Some plugin files contain multiple plugins; the `plugin` parameter
selects which one to use.

## Notes on Performance

Routing multiple audio groups through a single effect instance does
**not** mix them together; each group is processed independently.
However, each additional group increases CPU usage. For best
performance, effects should be applied only to the groups that
require them.

