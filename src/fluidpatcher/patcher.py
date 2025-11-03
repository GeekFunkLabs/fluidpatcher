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

from yaml import safe_load, safe_dump

from .bankfiles import Bank, SFPreset, MidiMessage, LadspaEffect
from .config import CONFIG, PATCHCORD
from .pfluidsynth import Synth, PLAYER_TYPES
from .router import Router


CC_DEFAULTS = [0] * 120
CC_DEFAULTS[0] = -1             # bank select
CC_DEFAULTS[7] = 100            # volume
CC_DEFAULTS[8] = 64             # balance
CC_DEFAULTS[10] = 64            # pan
CC_DEFAULTS[11] = 127           # expression
CC_DEFAULTS[32] = -1            # bank select LSB
CC_DEFAULTS[43] = 127           # expression LSB
CC_DEFAULTS[70:80] = [64] * 10  # sound controls
CC_DEFAULTS[84] = 255           # portamento control
CC_DEFAULTS[96:102] = [-1] * 6  # RPN/NRPN controls

SYNTH_DEFAULTS = {'synth.chorus.active': 1, 'synth.reverb.active': 1,
                  'synth.chorus.depth': 8.0, 'synth.chorus.level': 2.0,
                  'synth.chorus.nr': 3, 'synth.chorus.speed': 0.3,
                  'synth.reverb.damp': 0.0, 'synth.reverb.level': 0.9,
                  'synth.reverb.room-size': 0.2, 'synth.reverb.width': 0.5,
                  'synth.gain': 0.2}


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
    """

    def __init__(self, fluidsettings={}):
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
        self.bank = None
        self.soundfonts = {}
        self._players = {ptype: {} for ptype in PLAYER_TYPES}
        self._ladspafx = set()
        self._router = Router(fluid_default=False, fluid_router=False)
        self._synth = Synth(self._router.handle_midi,
                            CONFIG["fluidsettings"] | fluidsettings)
        self._router.synth = self._synth

    def load_bank(self, file='', raw=''):
        """Load bank from a file or text

        Parses a yaml stream from a string or file and stores as a
        Bank object. If successfully loaded from a file, updates
        'bankfile' in the config file. Resets the synth, updates paths
        in the Bank object, and applies values from the 'init' section
        of the bank.

        Args:
          file: Path or str, absolute or relative to 'bankpath'
          raw: string to parse directly
        """
        def read_bank(files, raw='', indent=0):
            text = ''
            if files:
                raw = (CONFIG["banks_path"] / files[-1]).read_text()
            for line in raw.splitlines(keepends=True):
                if '#include' in line:
                    i = line.index('#include')
                    f = line[i + 9:].rstrip()
                    if f not in files:
                        if line[:i].isspace():
                            line = read_bank(files + [f], indent=i)
                        else:
                            line = line[:i] + read_bank(files + [f])
                text += ' ' * indent + line
            return text

        self.bank = Bank(read_bank([file], raw))

        self._synth.reset()
        for zone in self.bank:
            for midi in zone.get('midifiles', {}).values():
                midi.file = CONFIG["midi_path"] / midi.file
            for fx in zone.get('ladspafx', {}).values():
                fx.lib = CONFIG["ladspa_path"] / fx.lib
        init = self.bank.root.get('init', {})
        for name, val in (SYNTH_DEFAULTS | init.get('fluidsettings', {})).items():
            self._synth[name] = val
        for msg in init.get('messages', []):
            self.send_midimessage(msg)

    def save_bank(self, file, raw=''):
        """Save a bank file
        
        Saves the active bank to `bankfile`. If `raw` is provided,
        it is parsed as the new bank and its exact contents are
        written to the file.

        Args:
          file (required): Path or str, absolute or relative to `bankdir`
          raw: exact text to save
        """
        if raw:
            self.bank = Bank(raw)
        else:
            raw = self.bank.dump()
        (CONFIG["banks_path"] / file).write_text(raw)

    def apply_patch(self, patch):
        """Apply the settings in a patch to the synth

        First checks that all soundfonts required by the bank are
        loaded. This should only happen when the bank is loaded, or
        possibly when patches are modified, added, or deleted. Next,
        applies all settings in the root level of the bank, followed
        by those specified in the patch.

        Args:
          patch (required): name of the patch to apply
        """
        # load all needed soundfonts at once to speed up patches
        # free memory of unneeded soundfonts
        for sf in set(self.soundfonts) - self.bank.soundfonts:
            self._synth.unload_soundfont(self.soundfonts[sf])
            del self.soundfonts[sf]
        for sf in self.bank.soundfonts - set(self.soundfonts):
            self.soundfonts[sf] = self._synth.load_soundfont(CONFIG["sounds_path"] / sf)
        # select presets
        for chan in range(1, self._synth['synth.midi-channels'] + 1):
            if p := self.bank[patch][chan]:
                self._synth.program_select(chan, self.soundfonts[p.file], p.bank, p.prog)
            else:
                self._synth.program_unset(chan)
        # fluidsettings
        for name, val in self.bank[patch]['fluidsettings'].items():
            self._synth[name] = val
        # players (e.g. sequences, arpeggios, midiloops, midifiles)
        for ptype in PLAYER_TYPES:
            for name, player in list(self._players[ptype].items()):
                if player not in self.bank[patch][ptype].values():
                    self._synth.player_remove(ptype, name)
                    del self._players[ptype][name]
            for name, player in self.bank[patch][ptype].items():
                if player not in self._players[ptype].values():
                    self._synth.player_add(ptype, name, player)
                    self._players[ptype][name] = player
        # ladspa effects
        if set(self.bank[patch]['ladspafx'].values()) != self._ladspafx:
            self._ladspafx = set()
            self._synth.fxchain_clear()
            for name, fx in (self.bank[patch]['ladspafx']).items():
                self._ladspafx.add(fx)
                self._synth.fxchain_add(name, fx)
            if self._ladspafx and PATCHCORD:
                self._synth.fxchain_add(
                    '_patchcord',
                    LadspaEffect(lib=PATCHCORD)
                )
                self._synth.fxchain_connect()
        # midi rules
        self._router.reset()
        for rule in self.bank[patch]['rules']:
            self.add_midirule(rule)
        # midi messages
        for msg in self.bank[patch]['messages']:
            self.send_midimessage(msg)

    def update_patch(self, name):
        """Update a patch from the current synth state

        Instruments and controller values can be changed by program
        change (PC) and continuous controller (CC) messages. This
        function reads the current value of all CCs and and presets
        on all MIDI channels and updates the indicated patch with
        those values.

        Args:
          name (required): name of the patch to update
        """
        self.bank.patch[name]['messages'] = []
        sfonts = {self.soundfonts[sf].id: sf for sf in self.soundfonts}
        for chan in range(1, self._synth['synth.midi-channels'] + 1):
            for cc, default in enumerate(CC_DEFAULTS):
                val = self._synth.get_cc(chan, cc)
                if val != default and default != -1 :
                    self.bank.patch[name]['messages'].append(
                        MidiMessage(type='cc', chan=chan, num=cc, val=val)
                    )
            id, bank, prog = self._synth.program_info(chan)
            if id not in sfonts:
                if chan in self.bank.patch[name]:
                    del self.bank.patch[name][chan]
            else:
                self.bank.patch[name][chan] = SFPreset(sfonts[id], bank, prog)

    def add_midirule(self, rule):
        """Add a midi rule to the Synth

        Directly add a midi rule to the Synth. This rule is applied
        after the patch rules. The rule is not added to the bank, and
        disappears if a new patch is applied.

        Args:
          rule: midi rule object
        """
        self._router.add(rule)

    def send_midimessage(self, msg):
        """Send a MIDI message to the synth, following MIDI rules

        Args:
          msg: midi message object
        """
        self._router.handle_midi(msg)

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
        self._synth[name] = val

    def set_callback(self, func):
        if func:
            self._router.callback = func
        else:
            self._router.callback = lambda event: None


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

