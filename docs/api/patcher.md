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

## Basic Pattern

A minimal interactive session looks like this:

```python
from fluidpatcher import FluidPatcher

fp = FluidPatcher()
fp.load_bank("mybank.yaml")
fp.apply_patch("Warm Pad")
```

Patches and banks can be changed with successive calls to
`apply_patch()` and `load_bank()`. This is all the API a program need
use to access all the functionality of banks.

::: fluidpatcher.FluidPatcher
    options:
      members:
        - __init__

The constructor initializes a FluidSynth engine using defaults from
`CONFIG["fluidsettings"]`, optionally overridden by user-supplied values.
It creates a custom MIDI router and installs it in the engine, which it
then starts and maintains for the FluidPatcher's entire lifetime.

FluidSynth's built-in logging (`None`) can be disabled (`-1`) or
redirected to a custom function that accepts a [fluid_log_level](
https://www.fluidsynth.org/api/group__logging.html
) and a message string.

::: fluidpatcher.FluidPatcher.load_bank

This method:

* Parses YAML into a `Bank` object
* Resolves `#include` directives recursively
* Resets the synth to a clean state
* Applies global initialization (`init.fluidsettings`, `init.messages`)
* Resolves filesystem paths for MIDI files and LADSPA plugins

If semantic validation fails (for example, a missing include file),
a `BankValidationError` is raised.

::: fluidpatcher.FluidPatcher.apply_patch

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

## Direct Synth Interaction

These methods can be used to directly interact with the running synth
instance and/or modify its state. They can be used to create UI-driven
ways of changing synth settings or adding controller behavior.

::: fluidpatcher.FluidPatcher.fluidsetting

::: fluidpatcher.FluidPatcher.fluidsetting_set

These methods provide controlled access to FluidSynth settings.

Only settings beginning with `synth.` may be modified. This ensures that
low-level or unsafe parameters cannot be altered accidentally.

::: fluidpatcher.FluidPatcher.send_midimessage

Sends a MIDI message directly to the synth, bypassing routing rules.

Typically used for:

* Explicit CC or program changes

::: fluidpatcher.FluidPatcher.add_midirule

Installs a MIDI rule directly into the live router.

Rules added this way:

* Take effect immediately
* Are **not stored** in the bank
* Are cleared when a patch is re-applied

This is useful for temporary mappings or UI-specific behavior.

::: fluidpatcher.FluidPatcher.set_callback

Installs a callback that observes MIDI events
*after routing but before they reach the synth*.

This is intended for:

* Visualizers
* UI Interaction with MIDI controllers
* Debugging tools

Passing `None` disables the callback.

## Bank Modification

The loaded bank can be modified in-place and saved back to disk.
Example applications are changing patch presets or splitting/layering
the keyboard interactively.

These methods provide basic tools for modifying banks. Bank editing is
further discussed in the Banks API section.

::: fluidpatcher.FluidPatcher.update_patch

Reads the *current live synth state* and writes it back into a patch.

Specifically, it:

* Scans all MIDI CCs on all channels
* Stores non-default controller values as MIDI messages
* Records current program selections

This is intended for **interactive patch creation**, where a performer
builds a sound using a controller and then captures it into YAML.

::: fluidpatcher.FluidPatcher.save_bank

Writes the current bank back to disk.

If raw YAML text is supplied, it is parsed and stored verbatim, allowing
round-trip editing without reformatting.

::: fluidpatcher.FluidPatcher.open_soundfont

Paths are resolved relative to `CONFIG["sounds_path"]`. If the soundfont
is already loaded, the current object is returned.

Normally this method does not need to be called directly—the bank
dynamically reports the set of soundfonts needed by all its patches,
and each call to `apply_patch()` enforces this set by loading/unloading
soundfonts as necessary. This both conserves RAM and facilitates rapid
switching between patches.

This method returns a SoundFont object that can be iterated to discover
patches when e.g. modifying a preset in a patch programatically.

* Iterating the SoundFont returns the valid `bank, prog` tuples.
* Element access using `bank, prog` returns
  the corresponding preset name.

## Related Types

The following classes, defined in `bankfiles.py` and documented in
the Banks API, are re-exported at the package level for convenience:

* `SFPreset` - SoundFont preset reference
* `MidiMessage` - Description of a single MIDI message
* `MidiRule` - Rule describing how incoming MIDI messages are filtered,
  transformed, or mapped

This type from `pfluidsynth.py` is also exposed at the package level.
It can be used to distinguish external MIDI events from events created
by MIDI rules in the callback.

* `FluidMidiEvent` - A MIDI message from a controller or external
  software, unaltered by MIDI rules.

## Summary

`FluidPatcher` is intentionally opinionated:

* YAML banks define *intent*
* The patcher enforces that intent consistently
* Live state is always derived from declarative configuration

If you understand `FluidPatcher`, you understand how the rest of the
library fits together.

