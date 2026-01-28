# Tutorial: Basics

**File:** `data/banks/tutorial/lesson01_basic.yaml`

This lesson introduces the basic structure of a bank file: selecting
soundfont presets, defining patches, and using simple MIDI rules for
layering and keyboard splits.

## Root-Level Rules

MIDI rules determine how incoming MIDI messages create synth events.
Rules defined at the root level apply to all patches unless overridden.

The first rule catches all note messages and passes them through
unchanged:

```yaml
rules:
- {type: note}
````

Because no other parameters are specified, any note received on a given
channel will generate sound using the preset assigned to that channel.

The second rule applies to control change messages:

```yaml
- {type: ctrl, chan: 1-16=1-16}
```

For the `chan` parameter, mapping a range to a range creates events on
**every** channel in the target range. For example, sending CC#7
(Volume) on any channel will adjust the volume of all channels.

## The `Single` Patch

The simplest patch assigns a single preset to a MIDI channel:

```yaml
Single:
  1: test.sf2:000:004
```

This selects program 4 (Electric Piano 1) from bank 0 of `test.sf2` on
channel 1. If your MIDI controller sends notes on channel 1 (the usual
default), this patch will immediately produce sound.

## The `Layered` Patch

The `Layered` patch assigns presets to two channels and adds a
patch-level rule:

```yaml
Layered:
  1: test.sf2:000:004
  2: test.sf2:000:007
  rules:
  - {type: note, chan: 1=2}
```

The root-level rule already sends notes from channel 1 to channel 1.
This additional rule sends the same notes to channel 2, creating a
layered sound using both presets.

Patch-level rules are added to the root rules when the patch is applied.

## The `Split` Patch

The `Split` patch divides the keyboard into two note ranges:

```yaml
Split:
  2: test.sf2:000:004
  3: test.sf2:000:033
  rules:
  - {type: note, chan: 1=2, num: F4-127}
  - {type: note, chan: 1=3, num: E1-E4=E0-E3}
```

Notes above F4 are routed to channel 2 (Electric Piano), while lower
notes are routed to channel 3 (Fingered Bass). Channel 1 is unused in
this patch to avoid triggering both sounds via the root-level rule.

The `num` parameter restricts which notes match a rule. In the second
rule, `num` also remaps the note range. Note values are scaled
proportionally, shifting all matching notes down by one octave.

## Complete Bank File

```yaml
rules:
- {type: note}
- {type: ctrl, chan: 1-16=1-16}

patches:
  Single:
    1: test.sf2:000:004

  Layered:
    1: test.sf2:000:004
    2: test.sf2:000:007
    rules:
    - {type: note, chan: 1=2}

  Split:
    2: test.sf2:000:004
    3: test.sf2:000:033
    rules:
    - {type: note, chan: 1=2, num: F4-127}
    - {type: note, chan: 1=3, num: E1-E4=E0-E3}
```

