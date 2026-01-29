# Tutorial: Players in Practice

**File:** `data/banks/tutorial/lesson04_players.yaml`

This tutorial demonstrates **all four player types** supported by
FluidPatcher:

* **Sequences** – timed, repeating MIDI patterns
* **Arpeggios** – patterns generated from held notes
* **MIDI Loops** – live recording and overdubbing
* **MIDI Files** – playback of `.mid` files

Each player is defined at the **root level**, so it can continue running
while patches are changed. All players are synchronized to the same
tempo to make it easy to combine them.

## Root-Level Setup

### Presets and Channels

```yaml
1:  test.sf2:000:004
2:  test.sf2:000:005
3:  test.sf2:000:033
10: test.sf2:128:000
11: test.sf2:128:000
```

Presets defined at the root level apply to all patches unless overridden.
Here we reserve:

* Channel 1–3 for melodic parts
* Channel 10 and 11 for drums

## Sequences

Sequences play predefined MIDI events on a clock.

Two sequences are defined here: a melodic pattern (`montuno`) and a drum
pattern (`disco`).

### `montuno`: Pattern-Based Sequence

```yaml
sequences:
  montuno:
    tdiv: 16
    tempo: 110
    events:
    - - nt:2:A3:100, nt:2:C3:100, nt:2:E3:100, nt:2:A1:100
    - - _, nt:2:C3:100, nt:2:E3:100, nt:2:A1:100
    - - _, nt:2:C3:100, nt:2:E3:100, +
    order: 1, 2, 2, 3
```

Key ideas demonstrated here:

* A sequence can contain **multiple patterns**
* Each pattern can contain **one or more tracks**
* The `order` list controls how patterns are played and repeated
* `+` sustains the previous note
* `nt` is an alias for `note`

This format is compact and good for algorithmic or harmonic material.

### `disco`: Grid-Style Sequence

```yaml
disco:
  tdiv: 16
  tempo: 110
  events: |
    nt:10:36:100  _             nt:10:42:100
    _             _             nt:10:46:100
    nt:10:36:100  nt:10:39:100  nt:10:42:100
    _             _             nt:10:46:100
```

This alternate format treats **columns as tracks** and **rows as steps**.
It’s especially readable for drum patterns and is visually similar to a
step sequencer or tracker.

### Controlling Sequences

The *Sequencer Control* patch starts and stops each sequence using a
toggle button.

```yaml
patches:
  Sequencer Control:
    rules:
    - {type: ctrl, num: button1, val: 0-127=0-1, play: montuno}
    - {type: ctrl, num: button2, val: 0-127=0-1, play: disco}
```

The transformed value determines playback:

* `0` → stop
* `1` → play

## Arpeggios

Arpeggios generate notes from what you play, rather than from a fixed
pattern.

```yaml
arpeggios:
  fastpattern:
    style: manual
    tempo: 110
    tdiv: 32
```

This arpeggio:

* Plays notes in the **order they were received**
* Advances quickly (32 steps per bar)
* Shares the same tempo as the sequences

### Using the Arpeggio

```yaml
patches:
  Play Arpeggios:
    rules:
    - {type: note, chan: 1, arpeggio: fastpattern}
```

Any notes you play on channel 1 are captured and replayed by the
arpeggiator as long as they’re held.

## MIDI Loops

MIDI loops record what you play and repeat it continuously.

```yaml
midiloops:
  loop1:
    beats: 4
    tempo: 110
```

This creates a four-beat loop synchronized with the other players.

### Recording and Playback

```yaml
patches:
  Looper Control:
    rules:
    - {type: note, loop: loop1}
    - {type: ctrl, num: button1, val: 0-127=0-1, play: loop1}
    - {type: ctrl, num: pad1, val: 127=1, record: loop1}
    - {type: ctrl, num: pad2, val: 127=0, record: loop1}
    - {type: ctrl, num: pad3, val: 127=-1, record: loop1}
```

This setup allows you to:

* Record notes into the loop
* Start and stop playback
* Add overdub layers
* Undo the last layer

Loops can grow organically during performance.

## MIDI File Playback

MIDI files are played using `midifiles`.

```yaml
midifiles:
  funktrack:
    file: funkjam2.mid
    barlength: 1000
    jumps: 9>2
    shift: 1
    tempo: 110
```

Features demonstrated here:

* Looping between arbitrary bars
* Shifting channels to avoid conflicts with live players
* Tempo synchronization with other players

### Controlling Playback

```yaml
patches:
  Backing Tracks:
    rules:
    - {type: ctrl, num: button1, val: 127=-1, play: funktrack}
    - {type: ctrl, num: button1, val: 0, play: funktrack}
```

A negative play value restarts playback; `0` pauses it.

## Putting It All Together

This bank is designed so you can:

* Start a drum and bass groove
* Layer arpeggiated chords
* Record live loops
* Bring in a backing track

—all while staying synchronized and switching patches freely.

The key takeaway is that **players generate events over time**, while
**rules decide when and how those players respond to your controller**.

Once that mental model clicks, combining players becomes intuitive and
powerful.

