# Players

**Players** are components that generate MIDI events automatically,
without requiring a live controller message for each event. They are
built on top of FluidSynth’s sequencer and MIDI file playback
facilities.

Different player types serve different musical roles:

* **Sequences** play predefined patterns of MIDI events.
* **Arpeggios** replay currently held notes in a repeating pattern.
* **MidiLoops** record incoming events and loop them.
* **MidiFiles** play back standard `.mid` files.

Players do not act on their own: they are started, stopped, or modified
by **rules**.

## Defining Players

Players are defined as **named entries** under sections corresponding to
each player type (`sequences`, `arpeggios`, `midiloops`, `midifiles`).
They may appear at the root level and/or within a patch.

* Patch-level players override root-level players with the same name.
* When a patch is applied, all existing players are dismissed unless
  they are defined at the root level.
* Player names should be unique within a bank to avoid ambiguity.

## Common Rule Parameters

These rule parameters allow MIDI messages to control players. The exact
behavior depends on the player type, but the parameters themselves are
shared.

* `play: <player>`
  Starts, stops, or seeks within a player. The transformed message value
  determines the action.

* `tempo: <player>`
  Sets the player tempo in beats per minute.

* `tap: <player>`
  Sets tempo based on the timing of the last three tap events.
  The transformed value specifies how many beats the interval
  represents.

* `swing: <player>` (`sequences`, `arpeggios`)
  Adjusts timing to create a swing feel.
  Values range from `0.5` (no swing) to `0.99`.

* `groove: <player>` (`sequences`, `arpeggios`)
  Applies volume scaling to emphasize rhythmic accents.

## Sequences

Sequences define looping musical patterns directly in the bank file.
They are designed for constructing rhythms, basslines, and backing
tracks in a compact, readable format.

A sequence consists of:

* **Patterns**, played one after another
* Each pattern containing one or more **tracks**
* Each track being a list of MIDI events

### Bank File Parameters

`events` *(required)*
: The event data, expressed as:

    * A nested list of patterns → tracks → events, or
    * A simplified form (single pattern or single track), or
    * A tracker-style text format:
        * Each line is a step
        * Columns are tracks
        * Blank lines separate patterns

    Special symbols:

    * `+` - sustain previous note
    * `_` - rest (no event)



`order`
: List specifying playback order of patterns (1-indexed)

      * `0` stops playback
      * Negative values jump backward
      * End of list loops to the beginning
      * Defaults to looping the first pattern.

`tempo`
: Beats per minute (default: `120`)

`tdiv`
: Step length as a division of a 4-beat measure
  (default: `8`, i.e. eighth notes)

`swing`
: Timing swing ratio (default: `0.5`)

`groove`
: Volume emphasis pattern
  Can be a single value or a list (default: `1`)

### Rule Effects

* `play <name>`

    * `< 0` - restart current pattern
    * `0` - stop playback
    * `> 0` - start at the specified position in `order` (1-indexed)
      If already playing, the current pattern finishes first

## Arpeggios

Arpeggios capture incoming note events and replay them repeatedly while
the notes are held.

### Bank File Parameters

`style` *(required)*
: Playback pattern:

    * `up` - ascending
    * `down` - descending
    * `both` - up then down
    * `chord` - all notes together
    * `manual` - order notes were played

`tempo`, `tdiv`, `swing`, `groove`
: Same meaning as for `sequences`

### Rule Effects

* `arpeggio: <name>`
  Notes matched by the rule are captured and played by the arpeggio.

## MidiLoops

MidiLoops record incoming MIDI events and replay them as a loop. Loops
support unlimited overdub layers and unlimited undo. 

### Bank File Parameters

`beats` *(required)*
: Loop length in beats.
  A value of `0` sets the length when the first loop closes.

`tempo`
: Initial tempo in bpm (default: `120`)

### Rule Effects

* `loop: <name>`
  Adds matched events to the current recording layer (if recording)

* `play: <name>`

    * `0` - stop playback and recording
    * nonzero - start playback from the beginning of the loop

* `record: <name>`

    * `> 0` - if playing, start recording a new layer; if not playing,
      begin playing and recording when the next event is captured.
    * `0` - stop recording, close the current layer
    * `< 0` - delete the last *n* layers

## MidiFiles

MidiFiles create FluidSynth MIDI file players that play events from
`.mid` files. Playback can loop, seek, and jump between musical
sections.

### Bank File Parameters

`file` *(required)*
: Path to the MIDI file.

`tempo`
: Playback tempo in bpm.
  If set, tempo messages in the file are ignored.

`barlength`
: Number of ticks per full measure (default: `1`). The ticks per beat is
  stored in the header of a MIDI file.

`jumps`
: A list of jump points of the form `[from]>[to]`. When playback reaches
  the end of bar `from` (as determined by `barlength`), it jumps to the
  start of bar `to`. A `to` value of `0` halts playback when the end of
  bar `from` is reached.

`shift`
: An integer value to shift the channel of all messages in the file up or
  down, to avoid conflict with controllers.

`mask`
: List of MIDI message types to ignore during playback.

### Rule Effects

* `play <name>`

    * `< 0` - restart from beginning or last position
    * `0` - pause
    * `> 0` - seek to the specified bar (fractional values allowed)
      If currently playing, the seek occurs at the end of the current bar

* `tempo <name>`
  Set the tempo to the `val` of the resulting message, overriding file
  tempo behavior as described above. Setting the tempo to `0` will
  resume observance of file tempo changes.

