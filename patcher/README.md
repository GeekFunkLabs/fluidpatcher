# Patcher


The _patcher_ directory contains all the code necessary to interpret [bank and config files](file_formats.md) and control FluidSynth. This API can thus be used to write different Python programs that can read the same bank files and produce the same functionality. To use it, copy this directory to the same location as your Python script and `import patcher` at the top of your script. Patcher requires only Python standard libraries and [oyaml](https://pypi.org/project/oyaml/), and a working version of [FluidSynth](https://www.fluidsynth.org/) installed on your system.

The example below shows a very simple text-based implementation that loads a specific bank file and allows the user to select and play its patches.

### Example

```python
import patcher

bankfile = 'mybank.yaml'

p = patcher.Patcher('myconf.yaml')
p.load_bank(bankfile)

n = 0
while True:
    p.apply_patch(n)
    print(f"Patch {n + 1}/{len(p.patches)}: {p.patches[n]}")
    n = int(input("choose patch: ")) - 1
```

## API

### class Patcher

**Patcher**(_cfgfile="", fluidsettings={}_)

A generic Python object that handles patches and banks and starts an instance of FluidSynth in a separate thread.
- Parameters:
  - _cfgfile_: YAML-formatted file with platform-/implementation-specific settings for FluidPatcher/FluidSynth
  - _fluidsettings_: a dictionary of opt: val settings to pass directly to FluidSynth

#### Public Attributes/Properties

- _cfg_: data structure holding config info
- _cfgfile_: Path object to file used to configure this Patcher
- _currentbank_: Path object to current bank
- _bankdir_: Path object to directory where banks are stored
- _sfdir_: Path object to directory where soundfonts are stored
- _mfilesdir_: Path object to directory for midi files
- _plugindir_ : Path object to effects plugins
- _banks_ : list of bank files in _bankdir_ and its directory tree
- _soundfonts_ : list of soundfonts in _sfdir_ and its directory tree
- _patches_ : list of patches in the current bank
- _sfpresets_ : list of presets in the single soundfont loaded by **load_soundfont**() as [_PresetInfo_](#class-fswrappresetinfo) objects; empty when in bank mode

#### Public Methods

**read_config**()

Called by the Patcher object on creation. Can be called later to return the full text contents of the file.
- Parameters:
  - none
- Returns: the contents of the config file

**write_config**(_raw=None_)

Write _self.cfg_ to _self.cfgfile_ as YAML-formatted text; if _raw_ is provided and parses, write that exactly. Most parameters will not take effect until the next restart.
- Parameters:
  - _raw_: exact text to write
- Returns: nothing

**load_bank**(_bankfile='', raw=''_)

Load a bank from a file or from raw yaml text. If successful, reset the synth, load all necessary soundfonts, and apply initial settings. Returns the full text of the file that was loaded. If called with no arguments, resets the synth with the currently-loaded bank.
- Parameters:
  - _bankfile_: bank file to load
  - _raw_: raw yaml string to parse as current bank
- Returns: the contents of the bank file

**save_bank**(_bankfile, raw=""_)

Save the current bank to a file
- Parameters:
  - _bankfile_: bank file to save
  - _raw_: full text of the YAML document to save; text is checked for validity first
- Returns: nothing

**apply_patch**(_patch_)

Choose a patch from the loaded bank by its name or index. Select soundfonts for specified channels, apply router rules, activate players and effects, send messages, etc.
- Parameters:
  - _patch_: index of the patch as int, or patch name as a string. If _None_, bank-level keywords are still applied
- Returns: a list of warnings, if any

**add_patch**(_name, addlike=None_)

Create a new empty patch, or one that copies all settings other than instruments from an existing patch
- Parameters:
  - _name_: a name for the new patch
  - _addlike_: index or name of an existing patch; if specified, copy settings into the new patch
- Returns: the index of the new patch

**update_patch**(_patch_)

Update the specified patch with the current instrument settings and any modified continuous controller (CC) messages. This makes it possible to copy a patch by calling **add_patch()** followed by **update_patch()**
- Parameters:
  - _patch_: index or name of the patch to update
- Returns: nothing

**delete_patch**(_patch_)

Delete a patch from the currently loaded bank
- Parameters:
  - _patch_: index or name of the patch to delete
- Returns: nothing

**load_soundfont**(_soundfont_)

Unloads all soundfonts, loads the specified soundfont, scans all its presets, and stores them as a list of [_PresetInfo_](#class-fswrappresetinfo) objects in _sfpresets_. Resets the synth to a default state and routes all incoming MIDI messages to channel 1.
- Parameters:
  - _soundfont_: soundfont file to load
- Returns: **False** if loading fails, **True** otherwise

**select_sfpreset**(_presetnum_)

If a single soundfont has been loaded by **load_soundfont()**, load a preset from _sfpresets_ to MIDI channel 1.
- Parameters:
  - _presetnum_: index of the preset
- Returns: a list of warnings, empty if none

**fluid_get**(_opt_)

Get the current value of a fluidsynth [setting](http://www.fluidsynth.org/api/fluidsettings.xml)
- Parameters:
  - _opt_: setting name
- Returns: the setting's current value as float, int, or str

**fluid_set**(_opt, val, updatebank=False, patch=None_)

Change a fluidsynth setting. To add the new setting in the current bank, call with _updatebank=True_ and the current patch so that the new bank setting is not overridden by any settings in the patch.
- Parameters:
  - _opt_: setting name
  - _val_: new value to set
  - _updatebank_: if True, add/update the fluidsetting in the current bank in memory
  - _patch_: if updating the bank, clear conflicting settings from the patch, specified using name or index
- Returns: nothing

**add_router_rule**(_rule=None, **kwargs_)

Add a rule describing how MIDI messages will be interpreted/acted upon. This function is called by **load_bank()** and **select_patch()** to add the rules in a bank file, but it can be called directly by an implementation to add additional rules if desired
- Parameters:
  - _rule_: string containing a [router rule](file_formats.md#keywords), or 'clear' to erase current router rules
  - _**kwargs_: router rule as a set of key=value pairs
- Returns: nothing

**send_event**(_msg=None, **kwargs_)

Sends a MIDI event to FluidSynth, passed either as a string or via keywords.
- Parameters:
  - _msg_: midi message as a [bank file](file_formats.md#keywords)-styled string (`<type>:<channel>:<par1>:<par2>`)
  - _**kwargs_: keyword parameters describing the midi message
    - _type_: one of `note`, `noteoff`, `cc`, `pbend`, `prog`, `kpress`, `cpress`
    - _chan_: the MIDI channel of the message
    - _par1_: first parameter of the message, can be an integer or note name for `note` messages
    - _par2_: second parameter of the message, not required for `pbend`, `prog`, `cpress`, `noteoff`
- Returns: nothing

**set_midimessage_callback**(_func_)

Sets a function to be called when MIDI messages are received by the synth, or when custom router rules that aren't otherwise handled are triggered by MIDI messages. This can be disabled by calling this function with _None_. MIDI messages will be passsed as python objects with `type`, `par1`, and `par2` attributes. Custom router rules will pass a python object with the transformed attributes of the routed MIDI message, additional attributes corresponding to the parameters of the rule, and a `val` attribute that is the result of `par1` or `par2` routing of the MIDI message, depending on whether it is a one- or two-parameter type.
- Parameters:
  - _func_: a function that can accept a python object as its single argument
- Returns: nothing

### class fswrap.PresetInfo

#### Attributes

- _bank_: bank number
- _prog_: program number
- _name_: preset name
