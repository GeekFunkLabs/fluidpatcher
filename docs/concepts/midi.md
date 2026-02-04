# MIDI Event Processing

All interaction with FluidSynth in FluidPatcher is driven by MIDI
messages. Incoming messages from connected MIDI controllers are matched
against routing rules defined in the bank or active patch, producing
synth events such as playing notes, modifying parameters, or controlling
players.

A single incoming message may match multiple rules, and each matching
rule generates a separate event.

## MIDI messages

FluidPatcher can send MIDI messages automatically when a bank is loaded
or a patch is applied. Messages can appear:

- In the root-level `init` section (sent once when the bank is loaded)
- In the root- and patch-level `messages` sections
 (sent when a patch is applied)

### Message syntax

Messages are written in bank files using a compact scalar form:

```yaml
<type>:<chan>:<num>:<val>
```

or, when `num` is not applicable:

```yaml
<type>:<chan>:<val>
```

System real-time messages (`clock:`, `start:`, `stop:`, `continue:`)
and system exclusive messages (`sysex:XX:XX:XX:...`) may also be sent
and routed.

### Message Types

MIDI channel messages (i.e. "voice" messages), have `chan` and `type`
parameters, as well as the parameters shown in the table below.

!!! info
    Incoming Note Off messages are normalized to Note On messages with a
    velocity of zero.

| Message        | `num`              | `val`                 |
|----------------|--------------------|-----------------------|
| Note On        | note number        | velocity              |
| Control Change | controller number  | value                 |
| Key Pressure   | note number        | pressure              |
| Program Change | –                  | program number        |
| Pitch Bend     | –                  | amount (-8192–8192)   |
| Aftertouch     | –                  | pressure              |

The `type` parameter has multiple aliases for each message type
(standard, short form, mido-style):

* Note On: `note`, `nt`, `note_on`  
* Control Change: `ctrl`, `cc`, `control_change`
* Program Change: `prog`, `pc`, `program_change`
* Pitch Bend: `pbend`, `pb`, `pitchwheel`
* Aftertouch (Channel Pressure): `cpress`, `cp`, `aftertouch`
* Key Pressure (Polyphonic Aftertouch): `kpress`, `kp`, `polytouch`

## MIDI rules

Rules define how incoming MIDI messages are matched, transformed,
and forwarded as synth events. Rules may appear at the root or patch
level under the `rules` key.

```yaml
rules:
- {type: note, chan: 1=2}
- {num: 74, val: 0-127=50-100, type: ctrl, chan: 1=2}
- type: cpress=ctrl
  num: 1
  chan: 1=2-5
```

Rules may be written inline or in block form, and key order is flexible.
Only the `type` parameter is required.

### Rule matching and transformation

Each rule matches incoming messages based on its parameters. By default,
a matching rule produces an event of the same type with the same values.
A rule may also transform the event by changing its type or parameters.

To convert one message type into another, use:

```yaml
type: <from>=<to>
```

### Parameter forms

The parameters `chan`, `num`, and `val` support the following forms:

* `<value>`
  Matches a single value.

* `<min>-<max>`
  Matches a range of values.

* `<from>=<to>`
  Matches a value and converts it to a new value.

* `<min>-<max>=<value>`
  Matches a range and converts all values to a single value.

* `<min>-<max>=<tomin>-<tomax>`
  Scales values proportionally across the target range.
  For `chan`, this creates an event on *each* target channel.

* `<from>=<tomin>-<tomax>`
  For `chan`, matches a single channel and produces events on all target
  channels. For `num` and `val`, behaves like `<from>=<tomin>`.

* `<min>-<max>*<mul>[+|-]<val>`
  Matches a range, applies a multiplier, and adds an offset.

If a parameter is omitted, it matches any incoming value and forwards
that value unchanged.

### Default routing

When a patch is applied, all existing rules are cleared. If no rule
routes note events to the synth, no sound will be produced. A minimal
default rule at the root level is usually sufficient:

```yaml
rules:
- {type: note}
```

## Extended rule parameters

Additional rule parameters control non-voice behavior, such as synth
settings and player control. Player-related parameters are documented
in the *Players* section. Rules may also have custom parameters
recognized by specific user programs.

* `fluidsetting: <setting>`
  Sets a FluidSynth
  [setting](https://www.fluidsynth.org/api/fluidsettings.xml)
  to the value of the routed message.

* `log: <power>`
  Applies a logarithmic
  [function](https://www.desmos.com/calculator/gactb1ql9e) when 
  to the message value. The rule must have a `val` parameter to set
  the ranges for the transform. The parameter specifies the power of 10
  to use (positive values only).

* `lsb: <num>`
  Sends the lower 7 bits of a 14-bit value to a second controller
  specified by `num`. The upper 7 bits are sent to the primary target.

Rules are **inclusive** - A rule can have multiple extended parameters,
all of which will trigger actions. Also, the resulting MIDI event is
still sent to the synth in most cases - rules with extended behavior
do not *absorb* the event.

## Counters

A counter stores values that can be incremented by rules and used to
set event values.

Counters are defined in `counters` items at the root or patch level.
Patch-level counters are reset each time a patch is applied, while
root-level counters retain their state across patches.

### Bank File Parameters

`min`, `max` *(required)*
: Range for the counter

`startval`
: Initial value (default: `min`)

`wrap`
: Wraps values if True (default: clamp to range).

### Rule Effects

* `counter: <counter name>`
  Increments the counter by an amount equal to the resulting event's
  `val` parameter.

