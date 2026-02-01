Here’s a clean **Miscellaneous** tutorial section you can drop straight into the docs. I’ve written it to explain *what exists, why it exists, and when you’d ever care*, without dragging the reader through internals unless they’re curious.

---

## Miscellaneous: Configuration and Errors

This section covers two things you’ll usually only notice when something goes wrong—or when you want to customize how fluidpatcher behaves globally:

* The **global configuration file**
* The **errors you might see when a bank file fails to load**

Neither of these affects day-to-day patch writing, but understanding them makes troubleshooting much easier.

---

## Global Configuration (`fluidpatcherconf.yaml`)

fluidpatcher keeps its global configuration in a YAML file, created automatically on first run.

### Where it lives

By default, the config file is stored at:

```
~/.config/fluidpatcher/fluidpatcherconf.yaml
```

You can override this location by setting the environment variable:

```
FLUIDPATCHER_CONFIG
```

If the file does not exist, fluidpatcher will:

1. Create the directory
2. Copy in a bundled default configuration
3. Populate default folders if they’re missing

---

### What’s in the config

At runtime, the configuration is loaded into a single mapping called `CONFIG`. Most values are paths and global settings rather than musical behavior.

Key entries include:

| Key             | Meaning                                          |
| --------------- | ------------------------------------------------ |
| `banks_path`    | Directory containing your `.yaml` bank files     |
| `sounds_path`   | Where SoundFont (`.sf2`) files live              |
| `midi_path`     | Default location for MIDI files                  |
| `ladspa_path`   | Where LADSPA plugins are searched for            |
| `fluidsettings` | Raw FluidSynth settings passed through unchanged |

Any key ending in `_path` is automatically converted into a `Path` object internally, so paths behave consistently across platforms.

If you omit `banks_path`, `sounds_path`, or `midi_path`, fluidpatcher fills in sensible defaults relative to the config file.

---

### LADSPA and the built-in patchcord

fluidpatcher includes a small LADSPA helper plugin called **patchcord**, used to route audio between synth channels and effects.

At startup, fluidpatcher attempts the following, in order:

1. Use a locally built `patchcord.so` if present
2. Fall back to a prebuilt binary matching your architecture
3. Disable patchcord entirely if neither is available

If patchcord is unavailable:

* No internal audio routing is performed
* The FluidSynth setting `synth.audio-groups` is forced to `1`
* LADSPA effects will not function

This fallback ensures fluidpatcher still runs cleanly on systems without LADSPA support.

---

### Saving changes

The configuration file is only written back to disk when explicitly saved. When that happens:

* Paths are converted back to POSIX strings
* Key order is preserved
* The file is overwritten atomically

Most users will never need to edit this file by hand, but it’s safe to do so.

---

## Bank File Errors

When a bank file fails to load, fluidpatcher raises structured exceptions that try to be helpful rather than cryptic.

All bank-related errors derive from a single base class:

```
BankError
```

This makes it easy to catch *any* bank failure at a high level, while still getting detailed diagnostics.

---

### Syntax errors: `BankSyntaxError`

This error means the YAML itself is malformed.

Typical causes include:

* Bad indentation
* Missing colons
* Unterminated flow mappings
* Invalid YAML literals

When possible, the error includes line and column information pointing directly at the problem.

Example output:

```
mapping values are not allowed here at line 27, column 14
```

This error happens *before* fluidpatcher looks at musical meaning—nothing in the file is interpreted yet.

---

### Validation errors: `BankValidationError`

This error means the YAML is valid, but the contents don’t make sense to fluidpatcher.

Common causes include:

* Missing required keys
* Unknown rule or message types
* Invalid parameter ranges
* Incorrect nesting
* Semantic mismatches between objects

Validation errors include a **path** that points to the failing node in the bank structure.

Example output:

```
Unknown rule type in patches.Rhodes.rules.2
```

This tells you exactly where fluidpatcher gave up, without requiring guesswork.

---

### Why errors are strict

fluidpatcher intentionally fails fast and loudly when a bank is invalid.

This avoids:

* Silent misrouting of MIDI
* Half-working patches
* Effects appearing to do nothing
* Inconsistent behavior between sessions

If a bank loads successfully, you can trust that every rule, player, and mapping is structurally sound.

---

## Takeaway

* The global config controls **where things live**, not how music behaves
* Bank files are validated strictly, with clear diagnostics
* Syntax errors mean “bad YAML”
* Validation errors mean “valid YAML, wrong meaning”

Most users will never touch this section—but when something breaks, it’s exactly where you want to look.

