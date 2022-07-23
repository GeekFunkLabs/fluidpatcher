"""
Description: a performance-oriented patch interface for fluidsynth
"""
import re, copy
from pathlib import Path
try:
    import mido
except ModuleNotFoundError:
    pass # mido is optional, only needed to read .syx and send to external devices
from . import fswrap, fpyaml

VERSION = '0.7.9'
FLUID_VERSION = '.'.join(map(str, fswrap.FLUID_VERSION))

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

LADSPAFX_PATCHCORD = {'patchcordxxx': {'lib': 'patchcord', 'audio': 'mono'}}

class Patcher:

    def __init__(self, cfgfile='', fluidsettings={}):
        self.cfgfile = Path(cfgfile) if cfgfile else None
        self.cfg = {}
        self.read_config()
        self._bank = {'patches': {}}
        self._soundfonts = set()
        self._fluid = fswrap.Synth(**{**self.cfg.get('fluidsettings', {}), **fluidsettings})
        self._fluid.msg_callback = None
        self._max_channels = fluidsettings.get('synth.midi-channels', 16)

    @property
    def currentbank(self):
        return Path(self.cfg['currentbank']) if 'currentbank' in self.cfg else ''

    @property
    def bankdir(self):
        return Path(self.cfg.get('bankdir', 'banks')).resolve()

    @property
    def sfdir(self):
        return Path(self.cfg.get('soundfontdir', 'sf2')).resolve()

    @property
    def mfilesdir(self):
        return Path(self.cfg.get('mfilesdir', '')).resolve()

    @property
    def plugindir(self):
        return Path(self.cfg.get('plugindir', '')).resolve()

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
        if raw:
            c = fpyaml.parse(raw)
            self.cfg = c
            if self.cfgfile: self.cfgfile.write_text(raw)
        else:
            self.cfgfile.write_text(fpyaml.render(self.cfg))

    def load_bank(self, bankfile='', raw=''):
    # load patches, settings from :bankfile
    # or parse :raw yaml data as bank
    # if no arguments just reset the synth
    # returns the yaml string
        if bankfile:
            try:
                raw = (self.bankdir / bankfile).read_text()
                bank = fpyaml.parse(raw)
                bank['patches'].values()
            except:
                if Path(bankfile).as_posix() == self.cfg['currentbank']:
                    self.cfg.pop('currentbank', None)
                raise
            else:
                self._bank = bank
                self.cfg['currentbank'] = Path(bankfile).as_posix()
        elif raw:
            bank = fpyaml.parse(raw)
            bank['patches'].values()
            self._bank = bank
        self._reset_synth()
        self._refresh_bankfonts()
        for opt, val in self._bank.get('init', {}).get('fluidsettings', {}).items():
            self.fluid_set(opt, val)
        for msg in self._bank.get('init', {}).get('messages', []):
            if isinstance(msg, fpyaml.SysexMsg): self._send_sysex(msg)
            else: self.send_event(msg)
        return raw

    def save_bank(self, bankfile, raw=''):
    # save current patches, settings in :bankfile
    # if :raw is provided, parse and save it exactly
        if raw:
            bank = fpyaml.parse(raw)
            bank['patches'].values()
            self._bank = bank
        else:
            raw = fpyaml.render(self._bank)
        (self.bankdir / bankfile).write_text(raw)
        self.cfg['currentbank'] = Path(bankfile).as_posix()

    def apply_patch(self, patch):
    # :patch number, name, or dict
        warnings = []
        patch = self._resolve_patch(patch)
        def merge(kw):
            try: return {**self._bank.get(kw, {}), **patch.get(kw, {})}
            except TypeError: return self._bank.get(kw, []) + patch.get(kw, [])
        # presets
        for ch in range(1, self._max_channels + 1):
            preset = patch.get(ch) or self._bank.get(ch)
            if preset:
                if not self._fluid.program_select(ch - 1, self.sfdir / preset.sf, preset.bank, preset.prog):
                    warnings.append(f"Unable to select preset {preset} on channel {ch}")
            else:
                self._fluid.program_unset(ch - 1)
        # sequencers, arpeggiators, players
        self._fluid.players_clear(save=[*merge('sequencers'), *merge('arpeggiators'), *merge('players')])
        for name, info in merge('sequencers').items():
            self._fluid.sequencer_add(name, **info)
        for name, info in merge('arpeggiators').items():
            self._fluid.arpeggiator_add(name, **info)
        for name, info in merge('players').items():
            fpath = self.mfilesdir / info['file']
            pchan = fpyaml.tochantups(info['chan'])[0] if 'chan' in info else None
            self._fluid.player_add(name, **{**info, 'file': fpath, 'chan': pchan})
        # fluidsettings
        for opt, val in merge('fluidsettings').items():
            self.fluid_set(opt, val)
        # ladspa effects
        self._fluid.fxchain_clear(save=merge('ladspafx'))
        for name, info in {**merge('ladspafx'), **LADSPAFX_PATCHCORD}.items():
            libfile = self.plugindir / info['lib']
            fxchan = fpyaml.tochanset(info['chan']) if 'chan' in info else None
            self._fluid.fxchain_add(name, **{**info, 'lib': libfile, 'chan': fxchan})
        self._fluid.fxchain_connect()
        # router rules
        self._fluid.router_default()
        rules = [*merge('router_rules')][::-1]
        if 'clear' in rules:
            self._fluid.router_clear()
            rules = rules[:rules.index('clear')]
        for rule in rules:
            self.add_router_rule(rule)
        # midi messages
        for msg in merge('messages'):
            if isinstance(msg, fpyaml.SysexMsg): self._send_sysex(msg)
            else: self.send_event(msg)
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

    def update_patch(self, patch):
    # update :patch in current bank with fluidsynth's present state
        patch = self._resolve_patch(patch)
        messages = set(patch.get('messages', []))
        for channel in range(1, self._max_channels + 1):
            info = self._fluid.program_info(channel - 1)
            if not info:
                patch.pop(channel, None)
                continue
            sfont, bank, prog = info
            sfrel = Path(sfont).relative_to(self.sfdir).as_posix()
            patch[channel] = fpyaml.SFPreset(sfrel, bank, prog)
            for cc, default in enumerate(CC_DEFAULTS):
                if default < 0: continue
                val = self._fluid.get_cc(channel - 1, cc)
                if val != default:
                    messages.add(fpyaml.MidiMsg('cc', channel, cc, val))
        if messages:
            patch['messages'] = list(messages)

    def delete_patch(self, patch):
        if isinstance(patch, int):
            name = self.patches[patch]
        else:
            name = patch
        del self._bank['patches'][name]
        self._refresh_bankfonts()

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for channel in range(0, self._max_channels):
            self._fluid.program_unset(channel)
        for sfont in self._soundfonts - {soundfont}:
            self._fluid.unload_soundfont(self.sfdir / sfont)
        if {soundfont} - self._soundfonts:
            if not self._fluid.load_soundfont(self.sfdir / soundfont):
                self._soundfonts = set()
                return False
        self._soundfonts = {soundfont}
        self.sfpresets = self._fluid.get_sfpresets(self.sfdir / soundfont)
        self._reset_synth()
        for channel in range(1, self._max_channels + 1):
            self._fluid.program_unset(channel - 1)
        self.add_router_rule(type="note", chan=f"2-{self._max_channels}=1")
        return True
        
    def select_sfpreset(self, presetnum):
        warnings = []
        p = self.sfpresets[presetnum]
        soundfont = list(self._soundfonts)[0]
        if not self._fluid.program_select(0, self.sfdir / soundfont, p.bank, p.prog):
            warnings = [f"Unable to select preset {p}"]
        return warnings

    def fluid_get(self, opt):
        return self._fluid.get_setting(opt)

    def fluid_set(self, opt, val, updatebank=False, patch=None):
    # :updatebank if true, add/update the fluidsetting in current bank
    # :patch current patch to remove fluidsetting from if updating bank
        self._fluid.setting(opt, val)
        if updatebank:
            if 'fluidsettings' not in self._bank:
                self._bank['fluidsettings'] = {}
            self._bank['fluidsettings'][opt] = val
            if patch != None:
                patch = self._resolve_patch(patch)
                if 'fluidsettings' in patch and opt in patch['fluidsettings']:
                    del patch['fluidsettings'][opt]

    def add_router_rule(self, rule=None, **kwargs):
    # :rule text or a RouterRule object
    # :kwargs router rule parameters, as text or values
        if rule == None:
            rule = {par: fpyaml.parse(str(val))
                    for par, val in kwargs.items()}
            rule = fpyaml.RouterRule(**rule)
        elif isinstance(rule, str):
            rule = fpyaml.parse(rule)
            rule = fpyaml.RouterRule(**rule)
        rule.add(self._fluid.router_addrule)

    def send_event(self, msg=None, **kwargs):
    # :msg text, RouterRule object, or 'clear'
    # :kwargs message parameters as list of key=value pairs
        if isinstance(msg, str):
            msg = fpyaml.parse(msg)
        elif msg == None:
            msg = {par: fpyaml.parse(str(val))
                   for par, val in kwargs.items()}
            msg = fpyaml.MidiMsg(**msg)
        self._fluid.send_event(msg.type, msg.chan, msg.par1, msg.par2)

    # private functions
    def _refresh_bankfonts(self):
        sfneeded = set()
        for patch in self._bank['patches'].values():
            for channel in patch:
                if isinstance(channel, int):
                    sfneeded.add(patch[channel].sf)
        for channel in self._bank:
            if isinstance(channel, int):
                sfneeded.add(self._bank[channel].sf)
        missing = set()
        for sfont in self._soundfonts - sfneeded:
            self._fluid.unload_soundfont(self.sfdir / sfont)
        for sfont in sfneeded - self._soundfonts:
            if not self._fluid.load_soundfont(self.sfdir / sfont):
                missing.add(sfont)
        self._soundfonts = sfneeded - missing

    def _resolve_patch(self, patch):
        if isinstance(patch, int):
            try: patch = self.patches[patch]
            except IndexError: patch = {}
        if isinstance(patch, str):
            patch = self._bank['patches'].get(patch, {})
        return patch if isinstance(patch, dict) else {}

    def _reset_synth(self):
        self._fluid.players_clear()
        self._fluid.fxchain_clear()
        self._fluid.router_default()
        self._fluid.reset()
        for opt, val in {**SYNTH_DEFAULTS, **self.cfg.get('fluidsettings', {})}.items():
            self.fluid_set(opt, val)

    def _send_sysex(self, msg):
        try:
            if not msg.data and msg.file:
                msg.data = [m.data for m in mido.read_syx_file(self.mfilesdir / msg.file)]
            if msg.dest == '' or "FLUID Synth" in msg.dest:
                for x in msg: self._fluid.send_sysex(x)
            else:
                if not hasattr(self, 'ports'): self.ports = {}
                for portname in self.ports:
                    if msg.dest in portname:
                        port = self.ports[portname]
                        break
                else:
                    for portname in mido.get_output_names():
                        if msg.dest in portname:
                            port = self.ports[portname] = mido.open_output(portname)
                            break
                for x in msg: port.send(mido.Message('sysex', data=x))
        except NameError:
            pass
