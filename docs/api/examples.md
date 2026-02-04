# Examples

FluidPatcher ships with several runnable examples that demonstrate
common usage patterns, from minimal scripting to interactive bank
editing. These examples are intended to be read alongside the API
reference—they show how the core objects behave in practice,
not just how they’re defined.

## Basic Example

```bash
python -m fluidpatcher.examples.basic
```

Make sure:

* A MIDI controller is connected
* `testbank.yaml` exists in your configured banks path
* Fluidsynth audio is routed to speakers or headphones

**What it demonstrates**

* Creating a `FluidPatcher` instance
* Loading a bank from YAML
* Enumerating patches in a bank
* Applying patches at runtime
* Leaving MIDI routing “as-is” so notes from a connected controller are
heard immediately

This is the smallest useful FluidPatcher program. It loads a bank file
and lets you step through its patches interactively from the terminal.

**How it works**

* Loads `testbank.yaml`
* Prints the available patch names
* Applies the first patch
* Loops, advancing to the next patch when you press Enter

No MIDI rules are defined in the script itself—this relies on the bank
configuration to route MIDI appropriately.

## Patch Adding/Removing

```bash
python -m fluidpatcher.examples.patch_add_remove
```

You’ll need:

* A valid SoundFont (`test.sf2` in the configured sounds path)
* A MIDI controller on channel 1 (or adjust `MIDI_CHANNEL`)

**What it demonstrates**

* Creating patches programmatically (without YAML)
* Adding and deleting patches while the program is running
* Enumerating presets from a SoundFont
* Using `SFPreset` and `MidiRule` directly
* Applying patches dynamically

This example shows that banks are not static files—they’re mutable data
structures that can be created, edited, and destroyed entirely in Python.

**How it works**

* Loads a SoundFont
* Creates an initial patch in code
* Defines a root-level MIDI rule so note events reach the synth
* Presents a simple text UI to:

  * Select patches
  * Add new patches
  * Change presets
  * Delete patches

This is especially useful if you’re building tools that generate or
manipulate banks rather than authoring them by hand.

## Live Bank Editor

```bash
python -m fluidpatcher.examples.live_bank_editor
```

Or, if installed via `pip`:

```bash
fpatcher-editor
```

Notes:

* YAML syntax and validation errors are shown in the status bar and
  printed to stdout for debugging
* Errors do not stop the editor—this is intentional
* MIDI and audio routing must be handled externally
  (e.g., JACK, ALSA, a DAW)

**What it demonstrates**

* Live parsing and validation of bank YAML
* Immediate feedback on syntax and validation errors
* Applying patches without restarting FluidPatcher
* Using FluidPatcher alongside a DAW
* Integrating FluidPatcher into a GUI application

This example is a full interactive editor for FluidPatcher bank files.
Edits are parsed as you type, and valid patches appear immediately in a
menu where they can be auditioned.

It’s intended both as a practical tool and as a reference for embedding
FluidPatcher in larger applications.

**Key features**

* Open and save YAML bank files
* Real-time error reporting (non-fatal)
* Patch menu populated from parsed bank contents
* Designed to run concurrently with external MIDI/audio routing

