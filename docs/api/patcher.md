# FluidPatcher API

The `FluidPatcher` class is the **primary public interface** to
FluidPatcher. It coordinates FluidSynth, YAML-defined banks, and
MIDI routing into a single, performance-oriented control surface.

Most applications—CLI tools, GUIs, or scripts—will interact almost
exclusively with this class.

Conceptually, `FluidPatcher` sits *above* the router and ctypes
FluidSynth wrapper, and *below* the user interface
(banks, UI, MIDI controllers).

```
        UI / Controller
              ↓
Bank  →  FluidPatcher
              ↓      ↘
            Router → FluidSynth
```

## Overview

`FluidPatcher` is responsible for:

* Loading and saving YAML bank files
* Managing the lifecycle of a running FluidSynth instance
* Loading and unloading soundfonts automatically
* Applying patches (programs, effects, players, rules)
* Sending and receiving MIDI messages
* Exposing safe access to FluidSynth settings

It maintains **live state**: switching patches modifies the running
synth immediately, without restarting the engine.

::: fluidpatcher.FluidPatcher
    options:
      members:
        - __init__
        - load_bank
        - apply_patch

## Lifecycle and Typical Usage

A minimal interactive session looks like this:

```python
from fluidpatcher import FluidPatcher

fp = FluidPatcher()
fp.load_bank("mybank.yaml")
fp.apply_patch("Warm Pad")
```

Once created, a `FluidPatcher` instance:

1. Starts a FluidSynth engine immediately
2. Maintains that engine for its entire lifetime
3. Applies changes incrementally as patches are switched or updated

## Initialization and Synth Control

### `__init__`

The constructor initializes FluidSynth using defaults from
`CONFIG["fluidsettings"]`, optionally overridden by user-supplied values.

Logging can be redirected or disabled entirely.

Key points:

* The synth starts immediately
* MIDI routing is active as soon as the object exists
* No bank is loaded by default

## Bank Management

### `load_bank()`

Loads a YAML bank from disk or raw text.

This method:

* Parses YAML into a `Bank` object
* Resolves `#include` directives recursively
* Resets the synth to a clean state
* Applies global initialization (`init.fluidsettings`, `init.messages`)
* Resolves filesystem paths for MIDI files and LADSPA plugins

If semantic validation fails (for example, a missing include file),
a `BankValidationError` is raised.

### `save_bank()`

Writes the current bank back to disk.

If raw YAML text is supplied, it is parsed and stored verbatim, allowing
round-trip editing without reformatting.

## Patch Application

### `apply_patch()`

This is the **core operation** of FluidPatcher.

Applying a patch performs the following steps in order:

1. Verify bank soundfonts are available and load/unload as needed
2. Set/unset presets for every MIDI channel
3. Apply FluidSynth settings defined by the patch
4. Instantiate MIDI players (sequences, arpeggios, loops, midifiles)
5. Rebuild the LADSPA effect chain if necessary
6. Reset and install MIDI routing rules
7. Emit root/patch MIDI messages

Patch application is **idempotent**: reapplying the same patch will
recreate its intended state exactly.

### `update_patch()`

Reads the *current live synth state* and writes it back into a patch.

Specifically, it:

* Scans all MIDI CCs on all channels
* Stores non-default controller values as MIDI messages
* Records current program selections

This is intended for **interactive patch creation**, where a performer
builds a sound using a controller and then captures it into YAML.

## SoundFont Handling

### `load_soundfont()`

Loads a soundfont on demand and caches it.

Normally this method does not need to be called directly—patches
reference soundfonts symbolically, and `apply_patch()` ensures they
are loaded automatically. This method returns a SoundFont object that
can be iterated to discover patches when e.g. modifying a preset
in a patch programatically.

Paths are resolved relative to `CONFIG["sounds_path"]`.

## MIDI Interaction

### `add_midirule()`

Installs a MIDI rule directly into the live router.

Rules added this way:

* Take effect immediately
* Are **not stored** in the bank
* Are cleared when a patch is re-applied

This is useful for temporary mappings or UI-specific behavior.

### `send_midimessage()`

Sends a MIDI message directly to the synth, bypassing routing rules.

Typically used for:

* Explicit CC or program changes
* Automation or scripting

## `set_callback()`

Installs a callback that observes MIDI events
*after routing but before they reach the synth*.

This is intended for:

* Visualizers
* Debugging tools
* Interactive UIs

Passing `None` disables the callback.

## FluidSynth Settings Access

### `fluidsetting()` / `fluidsetting_set()`

These methods provide controlled access to FluidSynth settings.

Only settings beginning with `synth.` may be modified.

This ensures that low-level or unsafe parameters cannot be altered
accidentally.

## Related Types

The following commonly-used types are re-exported at the package level
for convenience:

* `MidiMessage`
* `MidiRule`
* `SFPreset`
* `FluidMidiEvent`

They are defined in `bankfiles.py` and `pfluidsynth.py` and are documented
in later API sections.

## Summary

`FluidPatcher` is intentionally opinionated:

* YAML banks define *intent*
* The patcher enforces that intent consistently
* Live state is always derived from declarative configuration

If you understand `FluidPatcher`, you understand how the rest of the
library fits together.

