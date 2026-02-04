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

## Root-Level Presets

The patches in this bank are used for choosing which player to control,
rather than selecting sounds. The root-level presets in this bank apply
to all patches, so they are always available to the root-level players.
For clarity, presets are placed in the bank file near the players that
use them.

* Channel 1 is set to E.Piano 1 near the root-level `note` rule, since
  it is for live playing, arpeggios, and looping.

```yaml
1: test.sf2:000:004
rules:
- {type: note, chan: 1}
```

* Channels 2 and 10 are used by the sequences for keys and drums.

```yaml
2:  test.sf2:000:005
10: test.sf2:128:000
```

* Channels 4 and 12 are used by the MIDI file player for bass and drums.

```yaml
4:  test.sf2:000:033
12: test.sf2:128:000
```

## Sequences

Sequences play predefined MIDI events on a clock.

Two sequences are defined here: a melodic pattern (`montuno`) and a drum
pattern (`disco`).

### Pattern-Based Sequence: `montuno`

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

### Grid-Style Sequence: `disco`

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
step sequencer or tracker. Multiple patterns can be defined in the grid
by separating them with blank lines.

### Controlling Sequences

The *Sequencer Control* patch starts and stops each sequence using a
toggle button.

```yaml
Sequencer Control:
  rules:
  - {type: ctrl, num: button1, val: 0-127=0-1, play: montuno}
  - {type: ctrl, num: button2, val: 0-127=0-1, play: disco}
```

The transformed value determines playback:

* `0` → stop
* `1` → play (at step 1 of the playback `order`)

## Arpeggios

Arpeggios generate notes from what you play, rather than from a fixed
pattern.

```yaml
arpeggios:
  fastpattern: {style: manual, tempo: 110, tdiv: 16}
```

This arpeggio:

* Plays notes in the **order they were received**
* Advances quickly (16 steps per bar)
* Shares the same tempo as the sequences
* Is defined using the optional flow style for compactness

### Using the Arpeggio

```yaml
Play Arpeggios:
  rules:
  - {type: note, chan: 1, arpeggio: fastpattern}
```

When the *Play Arpeggios* patch is applied, any notes played on channel 1
are captured and replayed by the arpeggiator as long as they’re held.

## MIDI Loops

MIDI loops record what you play and repeat it continuously.

```yaml
midiloops:
  loop1: {beats: 4, tempo: 110}
```

This creates a four-beat loop synchronized with the other players.

### Recording and Playback

```yaml
Looper Control:
  rules:
  - {type: note, loop: loop1}
  - {type: ctrl, num: button1, val: 0-127=0-1, play: loop1}
  - {type: ctrl, num: pad1, val: 127=1, record: loop1}
  - {type: ctrl, num: pad2, val: 127=0, record: loop1}
  - {type: ctrl, num: pad3, val: 127=-1, record: loop1}
```

To start recording in the *Looper Control* patch, either:

* Press `pad1`. This primes recording, but doesn't begin until a note
  is played.
* Activate `button1` to start playback, then `pad1`. This starts
  recording events relative to when `button1` was pressed.

Either method can be used to synchronize loops to the start of a measure
when one of the other players is running.

Pressing `pad1` again will start recording a new overdub layer.
Pressing `pad2` will stop recording but playback will continue.
Pressing `pad3` at any time will undo the most recent layer.

## MIDI File Playback

MIDI files are played using `midifiles`.

```yaml
midifiles:
  funktrack:
    file: funkjam2.mid
    barlength: 1000
    jumps: 9>2
    shift: 2
    tempo: 110
```

Features demonstrated here:

* Setting the `barlength` (length of a measure) in ticks. The file used
  in this example uses 250 ticks per beat, so 1000 corresponds to a
  measure of four beats.

* Looping between arbitrary bars - when playback reaches the end of
  measure 9 it will loop back to the start of measure 2
  
* Shifting channels - The MIDI file has keys, drum, and bass tracks
  on channels 1, 2, and 10. Shifting these channels by 2 avoids conflicts
  with other players, and effectively silences the keys since there is
  no preset assigned to channel 3.

### Controlling Playback

```yaml
patches:
  Backing Tracks:
    rules:
    - {type: ctrl, num: button1, val: 127=-1, play: funktrack}
    - {type: ctrl, num: button1, val: 0, play: funktrack}
```

The *Backing Tracks* patch enables simplistic playback control.
A negative play value restarts playback from the last postion and `0`
pauses it, so `button1` acts a toggling *play/pause* control.

## Performance Design

This bank is designed so you can:

* Start a drum and bass groove
* Layer arpeggiated chords
* Record live loops
* Bring in a backing track

Switching patches effectively selects which player to control at a
given moment. This demonstrates that bank files can be used not just
for constructing sets of sounds, but also for creating
**varied performance modes**.

## Complete Bank File

```yaml
names:
  button1: 53
  button2: 54
  pad1: 50

1: test.sf2:000:004
rules:
- {type: note, chan: 1}

sequences:
  montuno:
    tdiv: 16
    tempo: 110
    events:
    - - nt:2:A3:100, nt:2:C4:100, nt:2:E4:100, nt:2:G#3:100
    - - _, nt:2:C4:100, nt:2:E4:100, nt:2:G3:100
    - - _, nt:2:C4:100, nt:2:G#3:100, +
    order: 1, 2, 2, 3
  disco:
    tdiv: 8
    tempo: 110
    events: | # alternate form; columns=tracks
      nt:10:36:100  _             nt:10:42:100 
      _             _             nt:10:46:100 
      nt:10:36:100  nt:10:39:100  nt:10:42:100 
      _             _             nt:10:46:100 

2: test.sf2:000:005
10: test.sf2:128:000

arpeggios:
  fastpattern: {style: manual, tempo: 110, tdiv: 16}

midiloops:
  loop1: {beats: 4, tempo: 110}

midifiles:
  funktrack:
    file: funkjam2.mid
    barlength: 1000
    jumps: 9>2
    shift: 2
    tempo: 110

4: test.sf2:000:033
12: test.sf2:128:000

patches:
  Sequencer Control:
    rules:
    - {type: ctrl, num: button1, val: 0-127=0-1, play: montuno}
    - {type: ctrl, num: button2, val: 127=1, play: disco}
    - {type: ctrl, num: button2, val: 0, play: disco}
  Play Arpeggios:    
    rules:
    - {type: note, chan: 1, arpeggio: fastpattern}
  Looper Control:
    rules:
    - {type: note, loop: loop1}
    - {type: ctrl, num: button1, val: 0-127=0-1, play: loop1}
    - {type: ctrl, num: button2, val: 0-127=0-1, record: loop1}
    - {type: ctrl, num: pad1, val: 127=-1, record: loop1}
  Backing Tracks:
    rules:
    - {type: ctrl, num: button1, val: 127=-1, play: funktrack}
    - {type: ctrl, num: button1, val: 0, play: funktrack}
```

