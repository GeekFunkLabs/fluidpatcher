# Banks API

The `bankfiles` module defines FluidPatcher’s **declarative data model**.
It turns YAML bank files into structured Python objects that can be
validated, inspected, modified, and written back to disk.

Advanced users and UI authors can use these classes directly to build
interactive editors, patch designers, or controller-driven workflows.

## The Bank Class

::: fluidpatcher.bankfiles.Bank
    options:
      members: false

Users don't instantiate Bank objects directly. They are created by
`FluidPatcher.load_bank` and a reference stored at `FluidPatcher.bank`.

```python
fp = FluidPatcher()
fp.bank
```

### Root vs Patch Data

Bank files are split into two conceptual areas:

* **Root level** — settings outside the `patches` block

* **Patch level** — settings within a named entry under `patches`

The `root` and `patch` attributes provide direct access to these two
areas of the parsed bank data, allowing them to be queried or modified
independently.

Indexing the `Bank` object by patch name returns a **merged view**
combining root and patch data using the following rules:

* SoundFont presets fall back to root values
* Lists (`messages`, `rules`) concatenate root + patch
* Dictionaries (`sequences`, `arpeggios`, etc.) merge, with patch values
  overriding root values

This merged view is computed dynamically and does **not** modify the
underlying bank structure. It should be treated as read-only; edits
should instead be made via the `root` and `patch` mappings.

## Modifying Banks Programmatically

Banks are mutable, and are designed to support interactive workflows
such as:

* Changing a patch’s SoundFont preset
* Inserting or removing MIDI rules
* Adjusting controller mappings
* Writing the modified bank back to disk

Example: change the program on channel 1 for a patch:

```python
fp.bank.patch["My Patch"][1] = SFPreset("piano.sf2", 0, 4)
```

## Mutating Objects and Serialization

When bank objects are loaded from YAML, they retain their original
serialized representation to support consistent round-trip
loading and saving. Bank object attributes can be edited in-place,
but if dumped to file they appear in their original form.

To update an object's YAML representation, it must replaced with a new
instance. Most bank object types (except `SFPreset`) provide a `copy()`
method to simplify this. `copy()` creates a new object using the
original parameters as defaults, with any provided keyword arguments
overriding selected fields.

```python
rule = fp.bank.patch["My Patch"]["rules"][2]

fp.bank.patch["My Patch"]["rules"][2] = rule.copy(
    chan=3,
    val="0-127=50-80"
)
```

This pattern preserves round-trip fidelity while supporting safe,
incremental edits.

!!! tip
    Replace edited objects with copies to persist them to disk.

## Bank Object Types

::: fluidpatcher.bankfiles.SFPreset

Represents a single SoundFont program selection. These objects
correspond to YAML entries such as:

```yaml
1: piano.sf2:000:004
```

They are lightweight and effectively immutable, making them safe to
replace programmatically.

::: fluidpatcher.bankfiles.MidiMessage

Represents a MIDI message that can be sent when loading a bank,
applying a patch, or from a `Sequence`.

Supported features include:

* Channel messages (note, CC, program change, etc.)
* System realtime messages and SysEx
* Shorthand aliases (`nt`, `cc`, `pc`)
* Scientific pitch notation (`C#4`)

Example:

```python
msg = MidiMessage(type="cc", chan=1, num=7, val=100)
fp.bank.patch["My Patch"]["messages"].append(msg)
```

::: fluidpatcher.bankfiles.MidiRule

A declarative routing directive connecting incoming MIDI messages to
synth events or programmatic actions.

Rules can:

* Filter by type, channel, controller, or value
* Remap ranges (e.g. slider → effect parameter)
* Translate between message types
* Trigger players, counters, or actions

::: fluidpatcher.bankfiles.Sequence

A step-sequenced event container supporting:

* Pattern-based sequencing
* Multi-track layouts
* Groove patterns
* Text or structured event syntax

::: fluidpatcher.bankfiles.Arpeggio

Defines a patterned arpeggiation behavior. Arpeggios are triggered by
incoming notes and can be reassigned or modified per patch.

::: fluidpatcher.bankfiles.MidiLoop

A looping MIDI recorder/player used for live looping and overdubbing.

::: fluidpatcher.bankfiles.MidiFile

MIDI file playback directive supporting:

* Jump points
* Tempo matching
* Note shifting to avoid collisions

::: fluidpatcher.bankfiles.LadspaEffect

Defines a LADSPA plugin instance and routing.

Effects are declarative:

* Applying a patch rebuilds the FX chain as needed
* Parameter changes can be driven by `MidiRule` mappings

::: fluidpatcher.bankfiles.Counter

A persistent state container used by routing rules.

Counters enable:

* Toggle behavior
* Stepped parameter changes
* Stateful controller logic

## Summary

The `bankfiles` module defines **everything that can appear in a bank**.

Key takeaways:

* YAML is parsed into validated Python objects
* Banks are mutable and round-trippable
* Patch access returns merged views, not copies
* Use the `copy()` method to save edited objects to disk

If `FluidPatcher` is the engine, `bankfiles` is the language it speaks.

