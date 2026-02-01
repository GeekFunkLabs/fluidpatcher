"""
High-level API for live patch control.

This module coordinates interaction between the synth
engine and Bank files. It handles:

  - loading and saving of banks
  - applying patch parameters (programs, controllers, volumes, etc.)
  - direct interaction with the synth and router
  - optional notification hooks for UI or CLI environments
"""

from pathlib import Path

from yaml import safe_load, safe_dump

from .bankfiles import Bank, SFPreset, MidiMessage
from .bankfiles import BankValidationError
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

SYNTH_DEFAULTS = {"synth.chorus.active": 1, "synth.reverb.active": 1,
                  "synth.chorus.depth": 8.0, "synth.chorus.level": 2.0,
                  "synth.chorus.nr": 3, "synth.chorus.speed": 0.3,
                  "synth.reverb.damp": 0.0, "synth.reverb.level": 0.9,
                  "synth.reverb.room-size": 0.2, "synth.reverb.width": 0.5,
                  "synth.gain": 0.2}


class FluidPatcher:
    """
    High-level controller for applying YAML-defined patches to FluidSynth.

    Manages bank loading, patch activation, MIDI routing, soundfonts,
    players, and synth settings.
    """

    def __init__(self, fluidsettings={}, fluidlog=None):
        """
        Create a FluidPatcher and start FluidSynth.

        Args:
          fluidsettings (dict):
              Additional FluidSynth settings that override defaults.

          fluidlog (callable | -1 | None):
              Callback accepting (level, message) or -1 to suppress logs.
        """
        self.bank = Bank("patches: {}")
        self._sfonts = {}
        self._router = Router(fluid_default=False, fluid_router=False)
        if fluidlog == -1:
            fluidlog = lambda lev, msg: None
        self._synth = Synth(
            fluidsettings=CONFIG["fluidsettings"] | fluidsettings,
            logfunc=fluidlog,
            midi_handler=self._router.handle_midi,
        )
        self._router.synth = self._synth

    @property
    def soundfonts(self):
        """dict[path, SoundFont]: A snapshot of the loaded soundfonts."""
        return self._sfonts

    def open_soundfont(self, path):
        """
        Load a soundfont and enumerate its presets.

        Args:
          path (str or Path): Filename or absolute path.

        Returns:
          SoundFont: iterable of presets, indexable by (bank, prog).
        """
        path = CONFIG["sounds_path"] / path
        if path.is_relative_to(CONFIG["sounds_path"]):
            sf = path.relative_to(CONFIG["sounds_path"]).as_posix()
        else:
            sf = path.as_posix()
        if sf not in self._sfonts:
            self._sfonts[sf] = self._synth.load_soundfont(path)
            self._sfonts[sf].file = sf
        return self._sfonts[sf]

    def load_bank(self, bankfile="", raw=""):
        """
        Load a bank from a YAML file or raw text.

        Args:
          bankfile (str or Path):
              Filename relative to CONFIG["banks_path"], or absolute.

          raw (str):
              YAML text to load directly, bypassing disk I/O.

        Raises:
          BankValidationError: if a referenced include file is missing
                               or other semantic validation fails.
        """
        def read_bank(files, raw="", indent=0):
            text = ""
            if files:
                try:
                    raw = (CONFIG["banks_path"] / files[-1]).read_text()
                except FileNotFoundError as e:
                    raise BankValidationError(
                        f"No such file {files[-1]}"
                    )
            for line in raw.splitlines(keepends=True):
                if "#include" in line:
                    i = line.index("#include")
                    f = line[i + 9:].rstrip()
                    if f not in files:
                        if line[:i].isspace():
                            line = read_bank(files + [f], indent=i)
                        else:
                            line = line[:i] + read_bank(files + [f])
                text += " " * indent + line
            return text
        self.bank = Bank(read_bank(
            [bankfile] if bankfile else [], raw
        ))
        self._synth.reset()
        for zone in self.bank:
            for midi in zone.get("midifiles", {}).values():
                midi.file = CONFIG["midi_path"] / midi.file
            for fx in zone.get("ladspafx", {}).values():
                fx.lib = CONFIG["ladspa_path"] / fx.lib
        init = self.bank.root.get("init", {})
        for name, val in (SYNTH_DEFAULTS | init.get("fluidsettings", {})).items():
            self._synth[name] = val
        for msg in init.get("messages", []):
            self.send_midimessage(msg)

    def save_bank(self, file, raw=""):
        """
        Write the current bank contents to disk.

        Args:
          file (str or Path):
              Output filename relative to CONFIG["banks_path"].

          raw (str):
              Exact YAML text to store.
        """
        if raw:
            self.bank = Bank(raw)
        else:
            raw = self.bank.dump()
        (CONFIG["banks_path"] / file).write_text(raw)

    def apply_patch(self, patch):
        """
        Apply a named patch from the loaded bank.

        Args:
          patch (str): The patch name to apply.
        """
        # load all needed soundfonts at once to speed up patches
        # free memory of unneeded soundfonts
        for sf in set(self._sfonts) - self.bank.soundfonts:
            self._synth.unload_soundfont(self._sfonts[sf])
            del self._sfonts[sf]
        for sf in self.bank.soundfonts - set(self._sfonts):
            self.open_soundfont(sf)
        # select presets
        for chan in range(1, self._synth["synth.midi-channels"] + 1):
            if p := self.bank[patch][chan]:
                self._synth.program_select(chan, self._sfonts[p.file], p.bank, p.prog)
            else:
                self._synth.program_unset(chan)
        # fluidsettings
        for name, val in self.bank[patch]["fluidsettings"].items():
            self._synth[name] = val
        # players (e.g. sequences, arpeggios, midiloops, midifiles)
        for ptype in PLAYER_TYPES:
            for name, player in list(self._synth.players[ptype]):
                if name not in self.bank[patch][ptype]:
                    self._synth.player_remove(ptype, name)
            for name, player in self.bank[patch][ptype].items():
                if name not in self._synth.players[ptype]:
                    self._synth.player_add(ptype, name, player)
        # ladspa effects
        wanted = self.bank[patch]["ladspafx"] | PATCHCORD
        if set(wanted) != set(self._synth.ladspafx):
            self._synth.fxchain_clear()
            for name, fx in wanted.items():
                self._synth.fxchain_add(name, fx)
            self._synth.fxchain_connect()
        # counters
        for name in list(self._router.counters):
            if name not in self.bank[patch]["counters"]:
                del self._router.counters[name]
        for name, counter in self.bank[patch]["counters"].items():
            if name not in self._router.counters:
                self._router.counters[name] = counter
                counter.val = counter.startval
            if name in self.bank.patch[patch].get("counters", {}):
                counter.val = counter.startval
        # midi rules
        self._router.reset()
        for rule in self.bank[patch]["rules"]:
            self.add_midirule(rule)
        # midi messages
        for msg in self.bank[patch]["messages"]:
            self.send_midimessage(msg)

    def update_patch(self, name):
        """
        Write current synth state back into a patch.

        Args:
          name (str): Patch name to modify in-place.
        """
        self.bank.patch[name]["messages"] = []
        sfonts = {self._sfonts[sf].id: sf for sf in self._sfonts}
        for chan in range(1, self._synth["synth.midi-channels"] + 1):
            for cc, default in enumerate(CC_DEFAULTS):
                val = self._synth.get_cc(chan, cc)
                if val != default and default != -1 :
                    self.bank.patch[name]["messages"].append(
                        MidiMessage(type="cc", chan=chan, num=cc, val=val)
                    )
            id, bank, prog = self._synth.program_info(chan)
            if id not in sfonts:
                if chan in self.bank.patch[name]:
                    del self.bank.patch[name][chan]
            else:
                self.bank.patch[name][chan] = SFPreset(sfonts[id], bank, prog)

    def add_midirule(self, rule):
        """
        Install a live MIDI rule after current bank rules

        Args:
          rule (MidiRule): A temporary rule
        """
        self._router.add(rule)

    def send_midimessage(self, msg):
        """
        Send a MIDI message directly to the synth.

        Args:
          msg (MidiMessage): MIDI message object.
        """
        self._synth.send_midievent(msg)

    def fluidsetting(self, name):
        """
        Retrieve a FluidSynth setting.

        Args:
          name (str): A FluidSynth setting name (e.g. 'synth.gain').

        Returns:
          Any: Current value of the setting.
        """
        return self._synth[name]
        
    def fluidsetting_set(self, name, val):
        """
        Modify a FluidSynth setting.

        Args:
          name (str): Setting name (only 'synth.' prefixes allowed).
          val (Any): Desired value.
        """
        self._synth[name] = val

    def set_callback(self, func):
        """
        Install a callback to observe MIDI events.

        Args:
          func (callable | None):
              Function taking a single event, or None to disable.
        """
        if func:
            self._router.callback = func
        else:
            self._router.callback = lambda event: None

