# Bank File Cookbook

Instead of complete bank files, this document provides *recipes*—short,
focused snippets demonstrating commonly desired or interesting bits of
functionality.

Each example is meant to be copied, adapted, and combined as needed.

## Volume Levels

FluidSynth exposes three independent volume controls:

* The global `synth.gain` setting
* Channel volume (CC#7)
* Channel expression (CC#11)

These levels are **multiplicative**, not additive, and can be used in
any combination. A common pattern is:

* **Channel volume** as a mixer-like “static” level per sound
* **Channel expression** for real-time performance dynamics
* **`synth.gain`** as a master output control

For example, this rule maps a slider to global gain:

```yaml
- {type: ctrl, num: slider1, fluidsetting: synth.gain, val: 0-127=0.0-1.0}
```

## Portamento Control

FluidSynth’s portamento parameter has a wide range
(0–16383 ms) and high resolution. For expressive control, it’s usually
best to combine:

* `lsb` for fine resolution
* `log` scaling for usable response across the range

Portamento must be enabled explicitly using the *portamento pedal*
(CC#65). In many cases, legato mode (CC#68) is also desirable.

```yaml
rules:
- {type: ctrl, chan: x, num: slider1=5, lsb: 37, val: 0-127=0-16383, log: 4}

messages:
- ctrl:x:65:64   # portamento on
- ctrl:x:68:64   # legato on
```

## Muting / Unsetting Channels

Sometimes you may want to turn off/mute a soundfont preset using using
your controller, rather than just changing patches-for example,
to silence individual tracks from a MIDI file or sequencer while it
continues playing.

Sending a program change with a value of `128` causes FluidSynth to
*unset* the channel, effectively muting it.

The example below creates a toggle button that switches channel 3
between *muted* and an Electric Piano sound:

```yaml
3: test.sf2:000:005

rules:
- {type: ctrl=prog, chan: 1=3, num: button1, val: 0-127=128-5}
```

## Parameter Control (RPN / NRPN)

The MIDI specification defines a general mechanism for controlling
arbitrary synth parameters by sending a **sequence** of control change
messages. These parameters fall into two categories:

* **RPN (Registered Parameter Numbers)** — standardized and widely supported
* **NRPN (Non-Registered Parameter Numbers)** — synth- or format-specific

FluidSynth supports both. In particular, the SoundFont specification
defines NRPNs for all generator parameters, making deep sound design
possible directly from MIDI.

### Pitch Bend Range (RPN 0)

Pitch bend range is standardized as **RPN 0**. To set a channel’s pitch
bend range to a fifth (±7 semitones), send the following messages:

```yaml
messages:
  - ctrl:1:101:0     # RPN select MSB
  - ctrl:1:100:0     # RPN select LSB
  - ctrl:1:6:7       # data entry MSB (7 semitones)
  - ctrl:1:38:0      # data entry LSB (0 cents, optional)
  - ctrl:1:100:127   # clear RPN LSB
  - ctrl:1:101:127   # clear RPN MSB
```

Clearing the RPN selection afterward is good practice to avoid
unintentionally modifying the same parameter later.

### Filter Control via NRPN

NRPNs can be used to control **all SoundFont generator parameters**.
This works by:

1. Selecting Soundfont 2.01 NRPN mode (CC#99 = 120)
2. Selecting a generator number (CC#98)
3. Sending data entry messages (CC#6 / CC#38)

Generator numbers and valid ranges are defined in
[section 8.1.3 of the SoundFont spec](https://www.synthfont.com/sfspec24.pdf#page=37).

The example below maps a slider to filter cutoff on channel 1.
A single controller movement triggers a sequence of rules that together
form a complete NRPN update.

```yaml
rules:
- {type: ctrl, chan: 1, num: slider1=99, val: =120}  # NPRN select MSB: Soundfont
- {type: ctrl, chan: 1, num: slider1=98, val: =8}    # NPRN select LSB: generator 8 - filter cutoff
- {type: ctrl, chan: 1, num: slider1=6, lsb: 38,
   val: 0-127=5000-8000, log: 0.02}                  # data entry
- {type: ctrl, chan: 1, num: slider1=99, val: =127}  # clear NRPN MSB
- {type: ctrl, chan: 1, num: slider1=98, val: =127}  # clear NRPN LSB
```

Finding a musically useful range often requires experimentation, as
generator response curves vary between soundfonts.

