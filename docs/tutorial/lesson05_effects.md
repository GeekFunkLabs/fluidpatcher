# Tutorial: Audio Effects with LADSPA

**File:** `data/banks/tutorial/lesson05_effects.yaml`

This tutorial demonstrates **audio effects** using LADSPA plugins.
Where previous lessons focused on MIDI routing and event generation,
the effects in this bank operate *after* MIDI has been rendered to sound.

This bank file demonstrates how to:

* Define LADSPA effects at the bank level
* Route audio from specific MIDI channels into effects
* Control effect parameters dynamically using MIDI rules
* Share effects across multiple patches

## Effect Units at the Root Level

All effects in this lesson are defined at the **root level** using the
`ladspafx` section:

```yaml
ladspafx:
  plate:
    lib: delay
    chan: 1
    audio: mono
    vals: {Delay: 0.1}
```

Each named entry creates an **effect unit**:

* The effect is instantiated automatically
* Audio is routed into it based on MIDI channel
* Control ports can be adjusted later using rules

Defining effects at the root level ensures they persist when switching
patches. However, unused effects can still consume CPU/RAM, so
defining them within patches may improve performance.

## Effects Used in This Lesson

LADSPA plugins are installed separately from FluidSynth/FluidPatcher.
A few example plugins are included when installing the LADSPA SDK
(e.g. `delay.so`). This bank uses two plugins from the
"Tom's Audio Plugins" package, which can be installed from the package
repositories of most distributions. For example, on Debian/Ubuntu:

```shell
sudo apt install tap-plugins
```

More plugins can be found on the web, or in package repos
(Hint: try `apt-cache search ladspa`).

### Plate Delay (`plate`)

```yaml
plate:
  lib: delay
  chan: 1
  audio: mono
  vals: {Delay: 0.1}
```

* Plays audio back with a delay
* Processes only channel 1
* `mono` alias sets audio ports to `Input, Output`
* Sets an initial delay time of 0.1 seconds

### Tremolo (`trem`)

```yaml
trem:
  lib: tap_tremolo
  audio: mono
  chan: 2
```

* Applies amplitude modulation
* Routed to channel 2
* Parameters are controlled live via MIDI

### Reverb (`reverb`)

```yaml
reverb:
  lib: tap_reverb
  audio: stereo
  chan: 2, 3
```

* Stereo reverb shared by channels 2 and 3
* Each channel is processed independently
* Creates depth without mixing instruments together

## Patch: FM Piano (Plate Reverb)

```yaml
FM Piano:
  1: test.sf2:000:005
  rules:
  - {type: note, chan: 1}
```

This patch routes notes directly to channel 1.

* Audio passes through the **plate delay**
* Assumes MIDI controller sends on channel 1
* No dynamic effect control

## Patch: Rhodes (Effect Modulation + Reverb)

```yaml
Rhodes:
  2: test.sf2:000:004
  rules:
  - {type: note, chan: 1=2}
  - {type: ctrl, num: slider1, val: 0-127=0-20, fx: trem>Freq}
  - {type: ctrl, num: slider2, val: 0-127=0-100, fx: trem>Depth}
```

This patch demonstrates **real-time effect control**.
Two sliders control tremolo parameters:

  * `Freq` – tremolo speed
  * `Depth` – modulation intensity

The `fx: [ladspafx name]>[port name]` syntax connects a MIDI rule
directly to a control port on the effect unit.

Audio is processed by the Tremolo effect first, followed by the Reverb
effect, according to the order the effects are defined in `ladspafx`.

## Patch: Clav (Shared Reverb)

```yaml
Clav:
  3: test.sf2:000:007
  rules:
  - {type: note, chan: 1=3}
```

The Clav patch:

* Routes notes to channel 3
* Shares the **reverb** effect with the Rhodes
* Does **not** pass through tremolo

## Key Concepts

* **Effects process audio, not MIDI**
* Effects are separate files/objects, obtained independently
* Routing is controlled by MIDI channel assignment
* Multiple patches can share the same effect unit
* MIDI rules don’t modify audio directly—they control effect parameters

Once effects are defined, they behave like part of the signal path,
responding naturally to your performance and controller input.

## Complete Bank File

```yaml
names:
  slider1: 13
  slider2: 14

ladspafx:
  plate:
    lib: delay
    chan: 1
    audio: mono
    vals: {Delay: 0.1}
  trem:
    lib: tap_tremolo
    audio: mono
    chan: 2
  reverb:
    lib: tap_reverb
    audio: stereo
    chan: 2, 3

patches:
  FM Piano:
    1: test.sf2:000:005
    rules:
    - {type: note, chan: 1}
  Rhodes:
    2: test.sf2:000:004
    rules:
    - {type: note, chan: 1=2}
    - {type: ctrl, num: slider1, val: 0-127=0-20, fx: trem>Freq}
    - {type: ctrl, num: slider2, val: 0-127=0-100, fx: trem>Depth}
  Clav:
    3: test.sf2:000:007
    rules:
    - {type: note, chan: 1=3}
```

