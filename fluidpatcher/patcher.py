"""A performance-oriented patch interface for FluidSynth

A Python interface for the FluidSynth software synthesizer that
allows combination of instrument settings, effects, sequences,
midi file players, etc. into performance patches that can be
quickly switched while playing. Patches are written in a rich,
human-readable YAML-based bank file format.

Includes:
- pfluidsynth.py: ctypes bindings to libfluidsynth and wrapper classes
    for FluidSynth's features/functions
- bankfiles.py: extensions to YAML and functions for parsing bank files

Requires:
- yaml
- libfluidsynth
"""

from pathlib import Path
from copy import deepcopy

from yaml import safe_load, safe_dump

from .bankfiles import Bank, SFPreset, MidiMessage, RouterRule
from .router import Router
from .pfluidsynth import Synth


class FluidPatcher:
    """An interface for running FluidSynth using patches
    
    Provides methods for:

    - reading YAML-based bank files
    - managing patches (apply, update, copy, delete)
    - directly controlling the Synth by modifying fluidsettings,
      manually adding router rules, and sending MIDI events
    
    Attributes:
      cfg: Config object providing access to settings in the config file
      bank: Bank object providing access to the active bank
      router_callback: a function to which the router echoes
        events for optional further processing
    """

    def __init__(self, cfgfile, **fluidsettings):
        """Creates FluidPatcher and starts FluidSynth
        
        Starts fluidsynth using settings found in yaml-formatted `cfgfile`.
        Settings passed via `fluidsettings` will override those in config file.
        See https://www.fluidsynth.org/api/fluidsettings.xml for a
        full list and explanation of settings. See documentation
        for config file format.
        
        Args:
          cfgfile (required): Path object pointing to config file
          fluidsettings: dictionary of additional fluidsettings
        """
        self.cfg = Config(cfgfile)
        self.bank = None
        self._router = Router(fluid_default=False)
        self.router_callback = self._router.callback
        self._synth = Synth(self._router.handle_midi, **self.cfg.fluidsettings | fluidsettings)
        self._router.synth = self._synth
        self._soundfonts = {}
        self._patchcord = {'_patchcord': {'lib': self.cfg.pluginpath / 'patchcord'}}

    def read_bank(self, bankfile='', raw=''):
        """Load bank from a file or text

        Parses a yaml stream from a string or file and stores as a
        Bank object. If successfully loaded from a file, updates
        'bankfile' in the config file. Resets the synth, updates paths
        in the Bank object, and applies values from the 'init' section
        of the bank.

        Args:
          bankfile: Path or str, absolute or relative to 'bankpath'
          raw: string to parse directly
        """
        if bankfile:
            raw = (self.cfg.bankpath / bankfile).read_text()
            self.cfg.bankfile = bankfile
        self.bank = Bank(raw)

        self._synth.reset()
        for zone in self.bank:
            for midi in zone.get('midiplayers', {}).values():
                midi.file = self.mfilesdir / midi.file
            for fx in zone.get('ladspafx', {}).values():
                fx.lib = self.plugindir / fx.lib
        init = self.bank.root.get('init', {})
        for name, val in (_SYNTH_DEFAULTS | init.get('fluidsettings', {})).items():
            self._synth[name] = val
        for msg in init.get('messages', []):
            self.send_event(msg)

    def write_bank(self, bankfile, raw=''):
        """Save a bank file
        
        Saves the active bank to `bankfile`. If `raw` is provided,
        it is parsed as the new bank and its exact contents are
        written to the file.

        Args:
          bankfile (required): Path or str, absolute or relative to `bankdir`
          raw: exact text to save
        """
        if raw:
            self.bank = Bank(raw)
        else:
            raw = self.bank.dump()
        (self.cfg.bankpath / bankfile).write_text(raw)
        self.cfg.bankfile = bankfile

    def apply_patch(self, patch):
        """Apply the settings in a patch to the synth

        First checks that all soundfonts required by the bank are
        loaded. This should only happen when the bank is loaded, or
        possibly when patches are modified, added, or deleted. Next,
        applies all settings in the root level of the bank, followed
        by those specified in the patch.

        Args:
          patch (required): patch index or name
        """
        # load all needed soundfonts at once to speed up patches
        # free memory of unneeded soundfonts
        for file in set(self._soundfonts) - self.bank.soundfonts:
            self._synth.unload_soundfont(self._soundfonts[file])
            del self._soundfonts[file]
        for file in self.bank.soundfonts - set(self._soundfonts):
            self._soundfonts[file] = self._synth.load_soundfont(self.cfg.sfpath / file)
        # select presets
        for channel in range(1, self._synth['synth.midi-channels'] + 1):
            if p := self.bank[patch][channel]:
                self._synth.program_select(channel, self._soundfonts[p.file], p.bank, p.prog)
            else:
                self._synth.program_unset(channel)
        # fluidsettings
        for name, val in self.bank[patch]['fluidsettings'].items():
            self._synth[opt] = val
        # sequencers, arpeggiators, midiplayers
        for name in self._synth.players:
            if name not in [*self.bank[patch]['sequencers'],
                            *self.bank[patch]['arpeggiators'],
                            *self.bank[patch]['midiplayers']]:
                self._synth.player_remove(name)
        for name, seq in self.bank[patch]['sequencers'].items():
            self._synth.sequencer_add(name, **seq.pars)
        for name, arp in self.bank[patch]['arpeggiators'].items():
            self._synth.arpeggiator_add(name, **arp.pars)
        for name, midi in self.bank[patch]['midiplayers'].items():
            self._synth.midiplayer_add(name, **midi.pars)
        # ladspa effects
        if self._synth.ladspafx != self.bank[patch]['ladspafx']:
            self._synth.fxchain_clear()
            for name, fx in (self.bank[patch]['ladspafx'] | self._patchcord).items():
                self._synth.fxchain_add(name, **fx.pars)
            if self._synth.ladspafx:
                self._synth.fxchain_connect()
        # router rules -- invert b/c fluidsynth applies rules last-first
        self._router.reset()
        for rule in self.bank[patch]['rules']:
            rule._add(self._router.add)
        # midi messages
        for msg in self.bank[patch]['messages']:
            self._router.handle_midi(msg)

    def update_patch(self, patch):
        """Update a patch from the current synth state

        Instruments and controller values can be changed by program
        change (PC) and continuous controller (CC) messages. This
        function reads the current value of all CCs and and presets
        on all MIDI channels and updates the indicated patch with
        those values.

        Args:
          patch (required): index or name of the patch to update
        """
        self.bank.patches[patch]['messages'] = []
        sfonts = {self._soundfonts[file].id: file for file in self._soundfonts}
        for channel in range(1, self._synth['synth.midi-channels'] + 1):
            for cc, default in enumerate(_CC_DEFAULTS):
                val = self._synth.get_cc(channel, cc)
                if val != default and default != -1 :
                    self.bank.patches[patch]['messages'] += [MidiMessage('cc', channel, cc, val)]
            id, bank, prog = self._synth.program_info(channel)
            if id not in sfonts:
                del self.bank[patch][channel]
            else:
                patch[channel] = SFPreset(sfonts[id], bank, prog)

    def copy_patch(self, src, dest):
        """Copy settings from one patch to another
        
        Args:
          src (required): index or name of source patch
          dest (required): index or name of destination patch, if it exists
            it is overwritten
        """
        self.bank.patches[dest] = deepcopy(self.bank.patches[src])

    def delete_patch(self, patch):
        """Delete a patch from the active bank

        Args:
          patch (required): index or name of the patch to delete
        """
        del self.bank[patch]

    def add_router_rule(self, **pars):
        """Add a router rule to the Synth

        Directly add a router rule to the Synth. This rule is applied
        after the patch rules. The rule is not added to the bank, and
        disappears if a new patch is applied.

        Args:
          pars: router rule parameters passed as keyword arguments
        """
        RouterRule(**pars)._add(self._router.addrule)

    def send_event(self, type, chan=1, num=0, val=0):
        """Send a MIDI event to the router

        Args:
          type (required): event type as string
          chan: MIDI channel
          num: note or controller number
          val: value
        """
        self._router.handle_midi(MidiMessage(type, chan, num, val))

    def fluidsetting(self, name):
        """Get the value of a fluidsynth setting

        Args:
          name (required): the fluidsynth setting
        """
        return self._synth[name]
        
    def fluidsetting_set(self, name, val):
        """Set a fluidsynth setting
        
        Only settings with a 'synth' prefix are allowed
        
        Args:
          name (required): the fluidsynth setting
          val (required): the value to set
        """
        if name.startswith('synth.'):
            self._synth[name] = val


class Config:
    """Class for accessing configuration data
    
    Attributes:
      bankfile: The active bank file, relative to bankpath.
        Setting it writes to the config file
      bankpath (read-only): root path to bank files
      sfpath (read-only): root path to soundfonts
      midipath (read-only): root path to MIDI files
      pluginpath (read-only): root path to LADSPA plugins
      fluidsettings (read-only): dictionary of fluidsynth settings    
    """

    def __init__(self, file):
        """Creates the Config object
        
        Args:
          file: Path or str, config file to load
        """
        self._file = Path(file)
        self._cfg = safe_load(file.read_text())
        self.bankpath = Path(self._cfg.get('bankpath', 'banks')).resolve()
        self.sfpath = Path(self._cfg.get('sfpath', self.bankpath / '../sf2')).resolve()
        self.midipath = Path(self._cfg.get('midipath', self.bankpath / '../midi')).resolve()
        self.pluginpath = Path(self._cfg.get('pluginpath', '')).resolve()
        self.fluidsettings = self._cfg.get('fluidsettings', {})

    @property
    def bankfile(self):
        return Path(self._cfg['bankfile']) if 'bankfile' in self._cfg else ''

    @bankfile.setter
    def bankfile(self, file):
        self._cfg['bankfile'] = Path(file).as_posix()
        self._file.write_text(safe_dump(self._cfg, sort_keys=False))


_CC_DEFAULTS = [0] * 120
_CC_DEFAULTS[0] = -1             # bank select
_CC_DEFAULTS[7] = 100            # volume
_CC_DEFAULTS[8] = 64             # balance
_CC_DEFAULTS[10] = 64            # pan
_CC_DEFAULTS[11] = 127           # expression
_CC_DEFAULTS[32] = -1            # bank select LSB
_CC_DEFAULTS[43] = 127           # expression LSB
_CC_DEFAULTS[70:80] = [64] * 10  # sound controls
_CC_DEFAULTS[84] = 255           # portamento control
_CC_DEFAULTS[96:102] = [-1] * 6  # RPN/NRPN controls

_SYNTH_DEFAULTS = {'synth.chorus.active': 1, 'synth.reverb.active': 1,
                  'synth.chorus.depth': 8.0, 'synth.chorus.level': 2.0,
                  'synth.chorus.nr': 3, 'synth.chorus.speed': 0.3,
                  'synth.reverb.damp': 0.0, 'synth.reverb.level': 0.9,
                  'synth.reverb.room-size': 0.2, 'synth.reverb.width': 0.5,
                  'synth.gain': 0.2}
