# Banks API

The `bankfiles` module defines FluidPatcher’s **declarative data model**.
It turns YAML bank files into structured Python objects that can be
validated, inspected, modified, and written back to disk.

Most users encounter this module indirectly via:

```python
fp = FluidPatcher()
fp.bank
```

Advanced users and UI authors can use these classes directly to build
interactive editors, patch designers, or controller-driven workflows.

## Design Philosophy

Banks are treated as **data**, not code:

* YAML is parsed into structured objects
* Objects validate themselves semantically
* Root-level defaults are inherited by patches
* Patches are merged dynamically when accessed
* The original YAML structure is preserved on dump

This allows FluidPatcher to act as both:

* a *live performance engine*, and
* a *round-trip YAML editor*

## The `Bank` Class

The `Bank` class represents a fully parsed and validated bank file.

Users typically interact with it via `FluidPatcher.bank`.

::: fluidpatcher.bankfiles.Bank
handler: python
options:
members:
- Bank
show_root_heading: true
show_source: false
heading_level: 3
:::

### Root vs Patch Data

Bank files are split into two conceptual areas:

* **Root level** — settings outside the `patches` block


* **Patch level** — settings within a named entry under `patches`


A bank consists of:

* **Root-level configuration**

  * `names`
  * `init`
  * shared players (sequences, arpeggios, effects, etc.)
* **Per-patch overrides**

  * programs
  * rules
  * messages
  * patch-specific players or effects

When accessing a patch via:

```python
zone = fp.bank["My Patch"]
```

you receive a **merged view**:

* Scalars fall back to root values
* Lists concatenate (root + patch, in that order)
* Dicts merge with patch values overriding root defaults

This merging happens dynamically and does not modify the underlying data.

---

### Iteration and SoundFont Discovery

`Bank` objects are iterable over all zones (root + patches), which allows
automatic discovery of required resources.

For example, FluidPatcher uses:

```python
fp.bank.soundfonts
```

to determine which `.sf2` files must be loaded before applying a patch.

---

### Modifying Banks Programmatically

Banks are mutable.

Common interactive workflows include:

* Changing a patch’s SoundFont preset
* Inserting or removing MIDI rules
* Adjusting controller mappings
* Writing the modified bank back to disk

Example: change the program on channel 1 for a patch:

```python
from fluidpatcher import SFPreset

fp.bank.patch["My Patch"][1] = SFPreset("piano.sf2", 0, 4)
```

---

## SoundFont Presets

### `SFPreset`

Represents a single SoundFont program selection.

::: fluidpatcher.SFPreset
handler: python
options:
members:
- SFPreset
show_root_heading: true
show_source: false
heading_level: 3
:::

These objects correspond to YAML entries like:

```yaml
1: piano.sf2:000:004
```

They are lightweight, immutable in practice, and safe to replace
programmatically.

---

## MIDI Messages

### `MidiMessage`

Represents a single MIDI message definition.

::: fluidpatcher.MidiMessage
handler: python
options:
members:
- MidiMessage
show_root_heading: true
show_source: false
heading_level: 3
:::

`MidiMessage` supports:

* Channel messages (note, cc, program change, etc.)
* Shorthand aliases (`nt`, `cc`, `pc`)
* Scientific pitch notation (`C#4`)
* Name resolution via the `names:` section

Example (programmatic construction):

```python
from fluidpatcher import MidiMessage

msg = MidiMessage(type="cc", chan=1, num=7, val=100)
fp.bank.patch["My Patch"]["messages"].append(msg)
```

Messages validate themselves when created.

---

## MIDI Routing Rules

### `MidiRule`

Describes how incoming MIDI messages are matched, transformed, or mapped.

::: fluidpatcher.MidiRule
handler: python
options:
members:
- MidiRule
show_root_heading: true
show_source: false
heading_level: 3
:::

Rules can:

* Filter by type, channel, controller, or value
* Remap ranges (e.g. slider → effect parameter)
* Translate between message types
* Trigger players, counters, or actions

Because rules are plain objects, editors can safely:

* Insert them at specific positions
* Modify ranges interactively
* Duplicate and tweak existing rules

---

## Time-Based Players

These objects define MIDI generators that run independently of input.

### `Sequence`

Step-sequenced event container.

::: fluidpatcher.bankfiles.Sequence
handler: python
options:
members:
- Sequence
show_root_heading: true
show_source: false
heading_level: 3
:::

Supports:

* Pattern-based sequencing
* Multi-track layouts
* Groove patterns
* Text or structured event syntax

---

### `Arpeggio`

Patterned arpeggiation definition.

::: fluidpatcher.bankfiles.Arpeggio
handler: python
options:
members:
- Arpeggio
show_root_heading: true
show_source: false
heading_level: 3
:::

Arpeggios are triggered by incoming notes and can be reassigned or
modified per patch.

---

### `MidiLoop`

Looping MIDI recorder/player.

::: fluidpatcher.bankfiles.MidiLoop
handler: python
options:
members:
- MidiLoop
show_root_heading: true
show_source: false
heading_level: 3
:::

Used for live looping and overdubbing workflows.

---

### `MidiFile`

MIDI file playback directive.

::: fluidpatcher.bankfiles.MidiFile
handler: python
options:
members:
- MidiFile
show_root_heading: true
show_source: false
heading_level: 3
:::

Supports:

* Jump points
* Tempo matching
* Note shifting to avoid collisions

---

## Audio Effects

### `LadspaEffect`

Defines a LADSPA plugin instance and routing.

::: fluidpatcher.bankfiles.LadspaEffect
handler: python
options:
members:
- LadspaEffect
show_root_heading: true
show_source: false
heading_level: 3
:::

Effects are declarative:

* Patch application rebuilds the FX chain as needed
* Parameter changes can be driven by `MidiRule` mappings

---

## State and Counters

### `Counter`

A persistent state container used by routing rules.

::: fluidpatcher.bankfiles.Counter
handler: python
options:
members:
- Counter
show_root_heading: true
show_source: false
heading_level: 3
:::

Counters enable:

* Toggle behavior
* Stepped parameter changes
* Stateful controller logic

---

## Summary

The `bankfiles` module defines **everything that can appear in a bank**.

Key takeaways:

* YAML is parsed into real, validated objects
* Banks are mutable and round-trippable
* Patches are merged views, not copies
* Objects are safe to construct and modify interactively
* FluidPatcher enforces consistency when applying changes

If `FluidPatcher` is the engine, `bankfiles` is the language it speaks.

