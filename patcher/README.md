# Patcher


The _patcher_ directory contains all the code necessary to interpret [bank and config files](file_formats.md) and control FluidSynth. This API can thus be used to write different Python programs that can read the same bank files and produce the same functionality. To use it, copy this directory to the same location as your Python script and `import patcher` at the top of your script. Patcher requires only Python standard libraries and [oyaml](https://pypi.org/project/oyaml/).

The example below shows a very simple text-based implementation that loads a specific bank file and allows the user to select and play its patches.

### Example

```python
import patcher

cfgfile = 'myconf.yaml'
bankfile = 'mybank.yaml'
p = patcher.Patcher(cfgfile)
p.load_bank(bankfile)

n = 0
while True:
    p.select_patch(n)
    print(f"Patch {n + 1}/{len(p.patches)}: {p.patches[n]}")
    n = int(input("select patch: ")) - 1
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

#### Public Methods

**set_midimessage_callback**(_func_)

Sets a function to be called when MIDI events are received by the synth. This can be bypassed by calling this function with _None_
- Parameters:
  - _func_: a function that takes a _fswrap.MidiMessage_ object as its single argument
- Returns: nothing

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

Load a bank file. If successful, reset the synth, apply bank-level settings, and load all necessary soundfonts. Returns the full text of the file that was loaded
- Parameters:
  - _bankfile_: bank file to load
  - _raw_: raw yaml string to parse as current bank
- Returns: the contents of the bank file

**save_bank**(_bankfile="", raw=""_)

Save the current bank to a file
- Parameters:
  - _bankfile_: bank file to save; if not provided, 'currentbank' from config file will be used
  - _raw_: full text of the YAML document to save; text is checked for validity first
- Returns: nothing

**select_patch**(_patch_)

Select a patch from the loaded bank by its name or index. Select soundfonts for specified channels, apply router rules, activate players and effects, send messages, etc.
- Parameters:
  - _patch_: index of the patch as int, or patch name as a string
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

Load a single soundfont, scan through all the presets in it and store them as a list of _PresetInfo_ objects in _sfpresets_. Also resets the synth to a default state and routes all incoming MIDI messages to channel 1. This function is not used to load the soundfonts in a bank file - that is handled by **load_bank()** - its purpose is for previewing the instruments in a soundfont when creating new patches or bank files. The soundfont is unloaded and _sfpresets_ cleared the next time **select_patch()** or **load_bank()** is called.
- Parameters:
  - _soundfont_: soundfont file to load
- Returns: **True** if successful, **False** if loading fails or there are no presets

**select_sfpreset**(_presetnum_)

If a single soundfont has been loaded by **load_soundfont()**, load a preset from _sfpresets_ to MIDI channel 1.
- Parameters:
  - _presetnum_: index of the preset
- Returns: **False** if a bank is loaded instead of a single soundfont or selecting the preset fails, **True** otherwise

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
  - _rule_: string containing a router rule [see wiki]
  - _**kwargs_: router rule as a set of key=value pairs
- Returns: nothing

### class PresetInfo

**PresetInfo**(_name, bank, prog_)

A simple container for storing information about a soundfont's presets

#### Attributes:
  - _name_: the preset name in the soundfont file
  - _bank_: the bank number of the preset
  - _prog_: the program number of the preset
