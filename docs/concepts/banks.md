# Bank Files

A **bank file** is a valid [YAML](https://yaml.org/) document with a
defined structure and a few additional constraints required by
FluidPatcher.

Bank files describe everything about a FluidSynth session: loaded
soundfonts, patches, routing rules, effects, and initialization
messages. Python code simply loads and applies them.

## Rules and restrictions

* The top-level of every bank file **must** be a mapping and contain a
  `patches` key.
* `null`/`None` values are not allowed. Any instance is treated as an
  error and causes a `BankValidationError`.
* Comma-separated strings (e.g. `A,B,C`) are automatically parsed as
  lists, even without brackets.
* All configuration happens either at the **root level** or within
  individual **patches**.

The smallest valid bank file looks like:

```yaml
patches: {}
```

## Root vs Patch

Bank files are split into two conceptual areas:

Root level
: Settings outside the `patches` block.
  Applied first whenever a patch is activated.

Patch level
: Settings within a named entry under `patches`.
  Override or extend the root when that patch is selected.

Most items may appear at either level; a few are **root-only**:

### Root-only items

`init`
: Commands executed **once**, when the bank is loaded—not on patch
  changes. This is primarily for MIDI messages and FluidSynth settings.

`names`
: A mapping of identifiers to numeric values.
  Names are substituted in MIDI rules and messages, helping keep bank
  files readable (e.g. `filtercutoff` → `74`).

## Includes

FluidPatcher supports inserting external files using:

```yaml
#include <filename>
```

Features:

* May appear anywhere in the file.
* Relative paths are resolved under `CONFIG["banks_path"]`.
* Included text is inserted *before YAML parsing*.
* If indented, the indent is applied to each included line.
* Includes may chain, but recursive loops are blocked.

This allows larger banks to be split into logical pieces or to share
common mappings such as controller aliases.

## Example

The bank file snippet below illustrates root vs patch precedence and
use of `names` and `#include`.
When a patch is applied, root sets reverb to 100, but the “Harpsichord”
patch overrides it to 0.
“Piano” retains the root value.

```yaml
names:
  #include ccnames.txt
messages: cc:1:reverb:100, cc:1:chorus:0
patches:
  Piano:
    1: defaultGM.sf2:000:000
  Harpsichord:
    1: defaultGM.sf2:000:006
    messages:
    - cc:1:reverb:0
```

```yaml
# ccnames.txt
reverb: 91
chorus: 93
```

!!! note
    It's good practice to give include-able files an extension other
    than `.yaml`, so they aren't mistaken for complete bank files.
