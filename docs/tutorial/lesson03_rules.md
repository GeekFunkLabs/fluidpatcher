# Tutorial: Advanced MIDI Rules

**File:** `data/banks/tutorial/lesson03_rules.yaml`

This lesson explores some of the more advanced things MIDI rules can do:
filtering events, transforming values, converting message types, maintaining
state with counters, and generating high-resolution control changes.

Each patch demonstrates a specific technique. While the examples are musical,
the patterns are broadly useful for MIDI processing and performance control.

## Filtering Notes by Velocity

The `VelFilter` patch demonstrates routing notes to *different instruments*
based on velocity, while ensuring that note releases are handled correctly.

```yaml
rules:
- {type: note, chan: mychan=1, val: 0-116}
- {type: note, chan: mychan=2, val: 117-127}
- {type: note, chan: mychan=2, val: 0}
```

Here:

* Notes with velocity **0–116** are routed to channel 1 (E.Piano 1)
* Notes with velocity **117–127** are routed to channel 2 (E.Piano 2)
* A third rule explicitly routes **note-off events** (`val: 0`) to channel 2

This last rule is important. Note messages with zero velocity release
notes. These are included in the range of the first rule for channel
1, but mapping both the upper velocity range and 0 velocity notes to
channel 2 requires two separate rules.

This patch illustrates a core idea:
**each rule independently decides whether to create a synth event.**

## Transforming Notes and Converting Message Types

Rules can reshape values *and* change message types.

```yaml
rules:
- {type: note, chan: mychan=3, num: 0-127*1-12}
- {type: cpress=ctrl, chan: mychan=3, num: modwheel}
```

In the `TypeRoute` patch:

* Incoming notes are transposed down one octave using the
  `min-max*mul+add` form of the `num` parameter
* Channel pressure (`cpress`) messages are converted into control changes
* The resulting control changes are sent as modulation (`modwheel`)

The first rule uses the alternate `min-max*mul+add` form for ranges.
Here, all matching note numbers are multiplied by 1 and then shifted by -12,
which makes octave transposition explicit and predictable.

Rules can freely map one message type into another. When mapping from
a message type that doesn't have a `num` to one that does, as in this
case, the rule must provide the `num` parameter.

## Incrementing Parameters with Counters

Rules can maintain internal state using **named counters**, which allows
messages to increment or decrement parameters.

A counter named `vol` is created at the root level:

```yaml
counters:
  vol: {min: 0, max: 120, startval: 70, wrap: no}
```

In the `IncVolume` patch, MIDI rules connect two momentary buttons
to the counter:

```yaml
rules:
- {type: ctrl, chan: mychan=4, num: pad1=7, val: 127=-10, counter: vol}
- {type: ctrl, chan: mychan=4, num: pad2=7, val: 127=10, counter: vol}
```

The `val` parameter of each rule captures values 1-127 (pressing the pad)
and ignores value 0 (releasing the pad).
The result of the `val` parameter increments the counter. Wrapping is
disabled (the default), so values are clamped at the limits.

The rule sets the `val` of the resulting MIDI message to the current
value of the counter.
In order for the volume CC to have the correct initial value,
a message is sent in the `init` block to initialize it:

```yaml
- ctrl:4:volume:70
```

If the counter were defined at the patch level, it would reset each
time the patch was applied.

## High-Resolution Control with Logarithmic Scaling

Some parameters benefit from both higher resolution and non-linear response.
Portamento/glide is a good example of this. Portamento is activated on
channel 5 when the bank is loaded using the message:

```yaml
- ctrl:5:glide_pedal:64
```

The following rule in the `Glide` patch implements smooth portamento
control:

```yaml
- {type: ctrl, chan: mychan=5,
   num: slider1=glide_msb, lsb: glide_lsb,
   val: 0-127=0-1000, log: 2.5}
```

* A slider generates a value scaled to **0–1000**
* The value is split into MSB and LSB parts
* Each part is sent to a different control change
* A logarithmic curve makes the slider more responsive at low values

## Complete Bank File

```yaml
names:
  mychan: 1
  slider1: 13
  pad1: 50
  pad2: 51
  modwheel: 1
  volume: 7
  glide_msb: 5
  glide_lsb: 37
  glide_pedal: 65

patches:
  VelFilter:
    1: test.sf2:000:004
    2: test.sf2:000:005
    rules:
    - {type: note, chan: mychan=1, val: 0-116}
    - {type: note, chan: mychan=2, val: 117-127}
    - {type: note, chan: mychan=2, val: 0}

  TypeRoute:
    3: test.sf2:000:067
    rules:
    - {type: note, chan: mychan=3, num: 0-127*1-12}
    - {type: cpress=ctrl, chan: mychan=3, num: modwheel}

  IncVolume:
    4: test.sf2:000:007
    rules:
    - {type: ctrl, chan: mychan=4, num: pad1=7, val: 127=-10, counter: vol}
    - {type: ctrl, chan: mychan=4, num: pad2=7, val: 127=10, counter: vol}
    - {type: note, chan: mychan=4}

  Glide:
    5: test.sf2:000:081
    rules:
    - {type: note, chan: mychan=5}
    - {type: ctrl, chan: mychan=5, num: slider1=glide_msb, lsb: glide_lsb,
       val: 0-127=0-1000, log: 2.5}

counters:
  vol: {min: 0, max: 120, startval: 70, wrap: no}

init:
    messages:
    - ctrl:4:volume:70
    - ctrl:5:glide_pedal:64
```
