# Tutorial: Messages and Controllers

**File:** `data/banks/tutorial/lesson02_messages.yaml`

This lesson introduces **named controllers**, **initialization messages**,
and **rules that translate incoming MIDI controls into synth events**.
Together, these features let you shape how controllers behave across
patches while still allowing per-patch customization.

## Named Controllers

In the `names` section, controller numbers are given symbolic names:

```yaml
names:
  volume: 7
  chorus: 93
  slider1: 13
  slider2: 14
```

These aliases make the bank easier to read and more portable. Instead of
remembering that CC#93 controls chorus, rules and messages can refer to
`chorus` directly. The value of `slider1` can be changed to match the
CC number sent by a physical slider on your controller, instead of
changing the value every time it is used in the bank file.

## Initialization Messages

The `init` section contains messages that are applied **once**, when the
bank is loaded:

```yaml
init:
  messages:
  - ctrl:1:volume:80
```

Here, volume is set to a medium level on channel 1 as a global starting
state. This message is *not* resent when switching patches—it
establishes a baseline for the entire bank.

## Patch-Change Messages

The `messages` section at the root level defines messages that are sent
**each time a patch is applied**, before any patch-specific messages:

```yaml
messages:
- ctrl:1:chorus:0
```

This ensures that chorus is reset to zero whenever a new patch is
applied, preventing effects from “leaking” between patches.

## Rules That Create Events

The rules section defines how incoming MIDI messages create synth events:

```yaml
rules:
- {type: note}
- {type: ctrl, num: slider1=volume}
- {type: ctrl, num: slider2=chorus}
```

The first rule creates note events for all incoming notes, unchanged.

The last two rules listen for control changes from physical sliders and
create new CC events targeting synth parameters:

* Moving `slider1` generates volume CC events
* Moving `slider2` generates chorus CC events

Each matching rule creates an event independently—multiple rules can
respond to the same incoming MIDI message if they apply.

## Patches and Local Overrides

This bank defines two simple patches:

```yaml
patches:
  EPiano:
    1: test.sf2:000:004
  Sax:
    1: test.sf2:000:067
```

Both use channel 1 and inherit the global rules and messages. The `Sax`
patch, however, adds a patch-level message:

```yaml
  Sax:
    1: test.sf2:000:067
    messages:
    - ctrl:1:chorus:99
```

Patch-level messages are sent **after** the root-level messages when the
patch is applied. In this case, chorus is reset to zero globally, then
set to a higher value specifically for the sax sound.

## Complete Bank File

```yaml
names:
  volume: 7
  chorus: 93
  slider1: 13
  slider2: 14

init:
  messages:
  - ctrl:1:volume:80

messages:
- ctrl:1:chorus:0

rules:
- {type: note}
- {type: ctrl, num: slider1=volume}
- {type: ctrl, num: slider2=chorus}

patches:
  EPiano:
    1: test.sf2:000:004
  Sax:
    1: test.sf2:000:067
    messages:
    - ctrl:1:chorus:99
```

