"""
Description: a performance-oriented patch interface for fluidsynth
"""
import re, copy
from pathlib import Path
from . import fswrap, fpyaml

VERSION = '0.5'

MAX_SF_BANK = 129
MAX_SF_PROGRAM = 128

CC_DEFAULTS = [(7, 7, 100), (11, 11, 127), (12, 31, 0), (44, 63, 0),
               (65, 65, 0), (70, 79, 64), (80, 83, 0), (84, 84, 255), 
               (85, 95, 0), (102, 119, 0)]
               
SYNTH_DEFAULTS = {'synth.chorus.depth': 8.0, 'synth.chorus.level': 2.0,
                  'synth.chorus.nr': 3, 'synth.chorus.speed': 0.3,
                  'synth.reverb.damp': 0.0, 'synth.reverb.level': 0.9,
                  'synth.reverb.room-size': 0.2, 'synth.reverb.width': 0.5,
                  'synth.gain': 0.2}


class Patcher:

    def __init__(self, cfgfile='', fluidsettings={}):
        self._cfgfile = Path(cfgfile) if cfgfile else None
        self.cfg = {}
        self.read_config()
        fluidsettings.update(self.cfg.get('fluidsettings', {}))
        self._fluid = fswrap.Synth(**fluidsettings)
        self._fluid.msg_callback = None
        self._max_channels = fluidsettings.get('synth.midi-channels', 16)
        self._bank = {'patches': {'No Patches': {}}}
        self._soundfonts = set()
        self.sfpresets = []

    @property
    def cfgfile(self):
        return self._cfgfile if self._cfgfile else None

    @property
    def currentbank(self):
        return Path(self.cfg['currentbank']) if 'currentbank' in self.cfg else None

    @property
    def sfdir(self):
        return Path(self.cfg.get('soundfontdir', 'sf2')).resolve()

    @property
    def bankdir(self):
        return Path(self.cfg.get('bankdir', 'banks')).resolve()

    @property
    def pluginpath(self):
        return Path(self.cfg.get('pluginpath', '')).resolve()

    @property
    def sysexdir(self):
        return Path(self.cfg.get('sysexdir', '')).resolve()

    @property
    def banks(self):
        return sorted([b.relative_to(self.bankdir) for b in self.bankdir.rglob('*.yaml')])

    @property
    def soundfonts(self):
        return sorted([sf.relative_to(self.sfdir) for sf in self.sfdir.rglob('*.sf2')])

    @property
    def patches(self):
        return list(self._bank['patches'])
        
    def set_midimessage_callback(self, func):
        self._fluid.msg_callback = func

    def read_config(self):
        if self.cfgfile == None:
            return fpyaml.render(self.cfg)
        raw = self.cfgfile.read_text()
        self.cfg = fpyaml.parse(raw)
        return raw

    def write_config(self, raw=None):
        if self.cfgfile == None:
            return
        if raw:
            c = fpyaml.parse(raw)
            self.cfgfile.write_text(raw)
            self.cfg = c
        else:
            self.cfgfile.write_text(fpyaml.render(self.cfg))

    def load_bank(self, bankfile='', raw=''):
    # load patches, settings from :bankfile
    # or parse :raw yaml data as bank
    # returns the yaml string
        if bankfile:
            raw = (self.bankdir / bankfile).read_text()
        if raw:
            self._bank = fpyaml.parse(raw)
        try:
            self._bank['patches'].values()
        except (NameError, KeyError, AttributeError):
            self._bank = {'patches': {'No Patches': {}}}
        else:
            if bankfile:
                self.cfg['currentbank'] = Path(bankfile).as_posix()
        self._reset_synth(full=True)
        self._reload_bankfonts()
        return raw

    def save_bank(self, bankfile='', raw=''):
    # save current patches, settings in :bankfile
    # if :raw is provided, parse and save it exactly
        if bankfile == '':
            bankfile = self.currentbank
        if raw:
            self._bank = fpyaml.parse(raw)
        else:
            raw = fpyaml.render(self._bank)
        (self.bankdir / bankfile).write_text(raw)
        self.cfg['currentbank'] = Path(bankfile).as_posix()

    def select_patch(self, patch):
    # :patch number, name, or dict
        warnings = []
        self.sfpresets = []
        activechannels = set()
        patch = self._resolve_patch(patch)
        self._reset_synth()
        for channel in range(1, self._max_channels + 1):
            preset = self._bank.get(channel) or patch.get(channel)
            if preset:
                if preset.sf not in self._soundfonts: self._reload_bankfonts()
                if not self._fluid.program_select(channel - 1, self.sfdir / preset.sf, preset.bank, preset.prog):
                    warnings.append(f"Unable to select preset {preset} on channel {channel}")
                else: activechannels |= {channel - 1}
            else:
                self._fluid.program_unset(channel - 1)
        for name, info in {**self._bank.get('ladspafx', {}), **patch.get('ladspafx', {})}.items():
            libfile = self.pluginpath / info['lib']
            if 'chan' in info:
                fxchannels = fpyaml.tochanset(info['chan']) & activechannels
            else:
                fxchannels = activechannels
            if fxchannels:
                self._fluid.fxunit_add(name, **{**info, 'lib': libfile, 'chan': fxchannels})
        self._fluid.fxchain_link()
        for name, info in patch.get('players', {}).items():
            if 'chan' in info:
                playerchan = fpyaml.tochantups(info['chan'])[0]
            else: playerchan = None
            self._fluid.player_add(name, **{**info, 'chan': playerchan})
        for name, info in patch.get('sequencers', {}).items():
            self._fluid.sequencer_add(name, **info)
        for name, info in patch.get('arpeggiators', {}).items():
            self._fluid.arpeggiator_add(name, **info)
        for opt, val in {**self._bank.get('fluidsettings', {}), **patch.get('fluidsettings', {})}.items():
            self.fluid_set(opt, val)
        for rule in self._bank.get('router_rules', []) + patch.get('router_rules', []):
            if rule == 'clear': self._fluid.router_clear()
            else: self.add_router_rule(rule)
        for msg in self._bank.get('messages', []) + patch.get('messages', []):
            if msg == 'default': self._send_cc_defaults()
            else: self._fluid.send_event(*msg)
        return warnings

    def add_patch(self, name, addlike=None):
    # new empty patch name :name, copying settings from :addlike
        self._bank['patches'][name] = {}
        if addlike:
            addlike = self._resolve_patch(addlike)
            for x in addlike:
                if not isinstance(x, int):
                    self._bank['patches'][name][x] = copy.deepcopy(addlike[x])
        return self.patches.index(name)

    def delete_patch(self, patch):
        if isinstance(patch, int):
            name = self.patches[patch]
        else:
            name = patch
        del self._bank['patches'][name]
        self._reload_bankfonts()

    def update_patch(self, patch):
    # update :patch in current bank with fluidsynth's present state
        patch = self._resolve_patch(patch)
        messages = patch.get('messages', [])
        for channel in range(1, self._max_channels + 1):
            info = self._fluid.program_info(channel - 1)
            if not info:
                if channel in patch:
                    del patch[channel]
                continue
            sfont, bank, prog = info
            sfrel = Path(sfont).relative_to(self.sfdir).as_posix()
            patch[channel] = fpyaml.SFPreset(sfrel, bank, prog)
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    val = self._fluid.get_cc(channel - 1, cc)
                    if val != default:
                        messages.append(fpyaml.MidiMsg('cc', channel, cc, val))
        if messages:
            patch['messages'] = messages

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for channel in range(0, self._max_channels):
            self._fluid.program_unset(channel)
        for sfont in self._soundfonts - {soundfont}:
            self._fluid.unload_soundfont(self.sfdir / sfont)
        if {soundfont} - self._soundfonts:
            if not self._fluid.load_soundfont(self.sfdir / soundfont):
                self._soundfonts = set()
                return
        self._soundfonts = {soundfont}
        self.sfpresets = []
        for bank in range(MAX_SF_BANK):
            for prog in range(MAX_SF_PROGRAM):
                name = self._fluid.get_preset_name(self.sfdir / soundfont, bank, prog)
                if not name: continue
                self.sfpresets.append(PresetInfo(name, bank, prog))
        self._reset_synth(full=True)
        self.add_router_rule(type='note', chan=f'2-{self._max_channels}=1')
        
    def select_sfpreset(self, presetnum):
        warnings = []
        if presetnum < len(self.sfpresets):
            p = self.sfpresets[presetnum]
            soundfont = list(self._soundfonts)[0]
            if not self._fluid.program_select(0, self.sfdir / soundfont, p.bank, p.prog):
                warnings.append(f"Unable to select preset {p}")
        else:
            warnings.append('Preset out of range')
        return warnings

    def fluid_get(self, opt):
        return self._fluid.get_setting(opt)

    def fluid_set(self, opt, val, updatebank=False, patch=None):
        self._fluid.setting(opt, val)
        if updatebank:
            if 'fluidsettings' not in self._bank:
                self._bank['fluidsettings'] = {}
            self._bank['fluidsettings'][opt] = val
            if patch:
                patch = self._resolve_patch(patch)
                if 'fluidsettings' in patch and opt in patch['fluidsettings']:
                    patch['fluidsettings'].remove(opt)

    def add_router_rule(self, rule={}, **kwargs):
    # :rule text or a RouterRule object
    # :kwargs router rule parameters to set explicity, as text or values
        if isinstance(rule, str):
            rule = fpyaml.parse(ruletext)
        if isinstance(rule, dict):
            for par, val in kwargs.items():
                if isinstance(val, str): rule[par] = fpyaml.parse(val)
            rule = fpyaml.RouterRule(**rule)
        rule.add(self._fluid.router_addrule)

    # private functions
    def _reload_bankfonts(self):
        sfneeded = set()
        for patch in self._bank['patches'].values():
            for channel in patch:
                if isinstance(channel, int):
                    sfneeded |= {patch[channel].sf}
        missing = set()
        for sfont in self._soundfonts - sfneeded:
            self._fluid.unload_soundfont(self.sfdir / sfont)
        for sfont in sfneeded - self._soundfonts:
            if not self._fluid.load_soundfont(self.sfdir / sfont):
                missing |= {sfont}
        self._soundfonts = sfneeded - missing

    def _resolve_patch(self, patch):
        if isinstance(patch, int):
            name = list(self._bank['patches'])[patch]
            patch = self._bank['patches'][name]
        elif isinstance(patch, str):
            name = patch
            patch = self._bank['patches'][name]
        return patch

    """
    def _parse_sysex(self, messages):
        outports = list_midi_outputs()
        openports = {}
        try:
            for port, data in [(x[0], x[1:]) for x in messages]:
                for name in [p for p in outports if port in p]:
                    if name not in openports:
                        openports[name] = mido.open_output(name)
                    if isinstance(data[0], str):
                        msg = mido.read_syx_file(self.sysexdir / data[0])
                    else:
                        msg = mido.Message('sysex', data=data)
                    openports[name].send(msg)
            for name in openports:
                openports[name].close()
        except:
            return "Failed to parse or send SYSEX"
    """

    def _send_cc_defaults(self, channels=[]):
        for channel in channels or range(1, self._max_channels + 1):
            for first, last, default in CC_DEFAULTS:
                for ctrl in range(first, last + 1):
                    self._fluid.send_cc(channel - 1, ctrl, default)

    def _reset_synth(self, full=True):
        self._fluid.router_default()
        self._fluid.fxchain_clear()
        if full:
            self._fluid.players_clear()
            self._fluid.sequencers_clear()
            self._fluid.arpeggiators_clear()
            self._send_cc_defaults()
            cfg_fset = self.cfg.get('fluidsettings', {})
            for opt, val in SYNTH_DEFAULTS.items():
                if opt in cfg_fset:
                    self.fluid_set(opt, cfg_fset[opt])
                else:
                    self.fluid_set(opt, val)
            init = self._bank.get('init', None)
            if init:
                for opt, val in init.get('fluidsettings', {}).items():
                    self.fluid_set(opt, val)
                for msg in init.get('messages', []):
                    self._fluid.send_event(*msg)
        else:
            self._fluid.players_clear(mask=self._bank.get('players', {}))
            self._fluid.sequencers_clear(mask=self._bank.get('sequencers', {}))
            self._fluid.arpeggiators_clear(mask=self._bank.get('arpeggiators', {}))


class PresetInfo:
    
    def __init__(self, name, bank, prog):
        self.name = name
        self.bank = bank
        self.prog = prog
