# Patcher API

All the code necessary to create implementations of FluidPatcher is contained in the _patcher/_ directory of this repository. Import `patcher` in a Python script to share the same functionality and bank file format, and create a "Patcher" object to start FluidSynth and load your banks and patches.

## Example

```python
import patcher

cfgfile = 'myconf.yaml'
bankfile = 'mybank.yaml'
p = patcher.Patcher(cfgfile)
p.load_bank(bankfile)

n = 0
while True:
    p.select_patch(n)
    print("Patch %d/%d: %s" % (n + 1, p.patches_count(), p.patch_name(n)))
    n = int(input("select patch: ")) - 1
```

## Public Functions

**read_yaml**(_text_)

Converts a YAML text stream, which can be a single document or multiple (separated by `---`), into a Python object using the additional FluidPatcher-specific formatting specifications defined by _yamlext.py_. Wraps _oyaml.safe_load_ so that dangerous embedded code will have no effect.
- Parameters:
  - _text_: YAML string
- Returns: a dict or list of dicts if there were multiple documents in the stream

**write_yaml**(_*args_)

Convert a Python object(s) to a (FluidPatcher-style) YAML stream. Wraps `oyaml.safe_dump`.
- Parameters:
  - _*args_: one or more Python objects to convert
- Returns: a YAML string

## class Patcher

**Patcher**(_cfgfile="", fluidsettings={}_)

A generic Python object that handles patches and banks and starts an instance of FluidSynth in a separate thread.
- Parameters:
  - _cfgfile_: YAML-formatted file with settings for FluidPatcher/FluidSynth
  - _fluidsettings_: a dict of settings to pass directly to FluidSynth

### Public Attributes/Properties

- _cfgfile_: file used to configure this Patcher
- _cfg_: data structure holding config info
- _sfdir_: directory where soundfonts are stored
- _bankdir_: directory where banks are stored
- _plugindir_ : path to effects plugins
- _currentbank_: the filename of the current bank
- _sfpresets_: when in single-soundfont-browsing state, a list of all presets in the soundfont; otherwise empty. Each element of the list is an _[SFPreset](https://github.com/albedozero/fluidpatcher/blob/5b39a721d2988c00ebbd882260186adcb126390e/patcher/yamlext.py#L9)_ object with the attributes _name_ (the preset name), _bank_, and _prog_.

### Public Methods

**read_config**()

Read the config file associated with the Patcher on creation
- Parameters:
  - none
- Returns: the contents of the config file

**write_config**(_raw=None_)

Write _self.cfg_ to _self.cfgfile_ as YAML-formatted text; if _raw_ is provided and parses, write that exactly
- Parameters:
  - _raw_: exact text to write
- Returns: nothing

**load_bank**(_bank=None_)

Load a bank file, apply any FluidSynth settings specified in the bank, load all necessary soundfonts and unload any unneeded ones to save memory
- Parameters:
  - _bank_: bank file to load or raw yaml string; if not provided, 'currentbank' from config file will be used
- Returns: the contents of the bank file

**save_bank**(_bankfile="", raw=""_)

Save the current bank to a file
- Parameters:
  - _bankfile_: bank file to save; if not provided, 'currentbank' from config file will be used
  - _raw_: full text of the YAML document to save; useful for preserving exact formatting/comments; text is checked for validity first
- Returns: nothing

**patch_name**(_patch_index_)

Get the name of a patch in the loaded bank by its index
- Parameters:
  - _patch_index_: index of the patch
- Returns: the patch name

**patch_names**()

Get a list of all patch names
- Parameters:
  - none
- Returns: a list of all patch names

**patch_index**(_patch_name_)

Get the index of a patch in the loaded bank
- Parameters:
  - _patch_name_: name of the patch
- Returns: the patch index

**patches_count**()

Get the total number of patches in the loaded bank
- Parameters:
  - none
- Returns: the number of patches

**select_patch**(_patch_)

Select a patch from the loaded bank by its name or index. Select soundfonts for specified channels, apply router settings, send CC/SYSEX messages, activate effects, etc.
- Parameters:
  - _patch_: index of the patch as int, or patch name as a string
- Returns: a list of warnings if any

**add_patch**(_name, addlike=None_)

Create a new patch, possibly copying settings from an existing one
- Parameters:
  - _name_: a name for the new patch
  - _addlike_: index or name of an existing patch; if specified, copy settings into the new patch
- Returns: the name of the new patch

**delete_patch**(_patch_)

Delete a new patch and unload its soundfonts if no other patches need them
- Parameters:
  - _patch_: index or name of the patch to delete
- Returns: nothing

**update_patch**(_patch_)

Update the current patch with Fluidsynth's channel settings, and save any CC values (excluding those that shouldn't be user-modified) if they have been changed from their defaults
- Parameters:
  - _patch_: index or name of the patch to update
- Returns: nothing

**load_soundfont**(_soundfont_)

Load a single soundfont (unloading others first to save memory), scan through all the presets in it and store them as a list of _SFPreset_s in the object's _sfpreset_ attribute
- Parameters:
  - _soundfont_: soundfont file to load
- Returns: **True** if successful, **False** if loading fails or there are no presets

**select_sfpreset**(_presetnum_)

Select a preset from the loaded soundfont to play on MIDI channel 1 in FluidSynth
- Parameters:
  - _presetnum_: index of the preset
- Returns: **False** if a bank is loaded instead of a single soundfont or selecting the preset fails, **True** otherwise

**fluid_get**(_opt_)

Get the current value of a fluidsynth [setting](http://www.fluidsynth.org/api/fluidsettings.xml)
- Parameters:
  - _opt_: setting name
- Returns: the setting's current value as float, int, or str

**fluid_set**(_opt, val, updatebank=False_)

Change a fluidsynth setting
- Parameters:
  - _opt_: setting name
  - _val_: new value to set
  - _updatebank_: if True, add/update the fluidsetting in the current bank in memory
- Returns: nothing

**link_cc**(_target, link='', type='effect', xfrm=RouterSpec(0, 127, 1, 0), **kwargs_)

Create a link between a CC message and a non-Synth parameter such as an effect control or fluidsynth setting
- Parameters:
  - _target_: name of the parameter to modify
  - _link_: <channel>:<cc> to monitor for changes
  - _type_: the type of parameter being linked
  - _xfrm_:  how to translate from the 0-127 CC value to the parameter's value, either as a _RouterSpec_ object or a string of the form `"<min>-<max>*<mul>+<add>"`
  - _**kwargs_: _chan_ and _cc_ can be passed as keyword arguments instead of _link_

**poll_cc**()

Scan through the list of current CC links, see if any have changed, and modify the corresponding parameter(s); must be called in the event loop of your implementation for CC links to work
- Parameters:
  - none
- Returns: a dictionary of return values with the link target as key, for those that need it (i.e. patch change type)

**cclinks_clear**(_type=''_)

Clear CC links of the given type, or all links if no type is given
- Parameters:
  - _type_: the type of parameter being linked
- Returns: nothing
