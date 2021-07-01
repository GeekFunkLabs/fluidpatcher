"""
Description: a performance-oriented patch interface for fluidsynth
"""
import re, copy
from pathlib import Path
import oyaml, mido
from . import fswrap, fpyaml

MAX_SF_BANK = 129
MAX_SF_PROGRAM = 128

CC_DEFAULTS = [(7, 7, 100), (11, 11, 127), (12, 31, 0), (33, 42, 0),
               (43, 43, 127), (44, 63, 0), (65, 65, 0), (70, 79, 64),
               (80, 83, 0), (84, 84, 255), (85, 95, 0), (102, 119, 0)]
               
SYNTH_DEFAULTS = {'synth.chorus.depth': 8.0, 'synth.chorus.level': 2.0,
                  'synth.chorus.nr': 3, 'synth.chorus.speed': 0.3,
                  'synth.reverb.damp': 0.0, 'synth.reverb.level': 0.9,
                  'synth.reverb.room-size': 0.2, 'synth.reverb.width': 0.5,
                  'synth.gain': 0.2}

VERSION = '0.5'


class PatcherError(Exception):
    pass


class PresetInfo:
    
    def __init__(self, name, bank, prog):
        self.name = name
        self.bank = bank
        self.prog = prog


class Patcher:

    def __init__(self, cfgfile='', fluidsettings={}):
        self._cfgfile = cfgfile
        self.cfg = {}
        self.read_config()
        fluidsettings.update(self.cfg.get('fluidsettings', {}))
        self._fluid = fswrap.Synth(**fluidsettings)
        self._max_channels = fluidsettings.get('synth.midi-channels', 16)
        self._bank = {'patches': {'No Patches': {}}}
        self._soundfonts = set()
        self._cc_links = []
        self.sfpresets = []

    @property
    def cfgfile(self):
        if self._cfgfile == '':
            return None
        else:
            return Path(self._cfgfile)

    @property
    def currentbank(self):
        if 'currentbank' in self.cfg:
            return Path(self.cfg['currentbank'])
        else:
            return None

    @property
    def sfdir(self):
        return Path(self.cfg.get('soundfontdir', 'sf2'))

    @property
    def bankdir(self):
        return Path(self.cfg.get('bankdir', 'banks'))

    @property
    def plugindir(self):
        return Path(self.cfg.get('plugindir', ''))

    @property
    def sysexdir(self):
        return Path(self.cfg.get('sysexdir', ''))

    @property
    def banks(self):
        return sorted([b.relative_to(self.bankdir) for b in self.bankdir.rglob('*.yaml')])

    @property
    def soundfonts(self):
        return sorted([sf.relative_to(self.sfdir) for sf in self.sfdir.rglob('*.sf2')])

    @property
    def patches(self):
        return list(self._bank['patches'])
        
    @staticmethod
    def parse_fpyaml(text):
        if '---' in text:
            return oyaml.safe_load_all(text)
        return oyaml.safe_load(text)

    @staticmethod
    def render_fpyaml(*args):
        if len(args) > 1:
            return oyaml.safe_dump_all(args)
        return oyaml.safe_dump(args[0])

    @staticmethod
    def list_midi_outputs():
        return mido.get_output_names()

    @staticmethod
    def list_midi_inputs():
        return mido.get_input_names()

    def set_midimessage_callback(self, func):
        self._fluid.callback = func
    
    def clear_midimessage_callback(self):
        self._fluid.callback = None

    def read_config(self):
        if self.cfgfile == None:
            return self.render_fpyaml(self.cfg)
        raw = self.cfgfile.read_text()
        try:
            self.cfg = self.parse_fpyaml(raw)
        except (oyaml.YAMLError, IOError):
            raise PatcherError("Bad configuration file")
        return raw

    def write_config(self, raw=None):
        if self.cfgfile == None:
            return
        if raw:
            try:
                c = self.parse_fpyaml(raw)
            except (oyaml.YAMLError, IOError):
                raise PatcherError("Invalid config data")
            else:
                self.cfgfile.write_text(raw)
                self.cfg = c
        else:
            self.cfgfile.write_text(self.render_fpyaml(self.cfg))

    def load_bank(self, bank=None):
    # load patches, settings from :bank yaml string or filename
    # if :bank is None, reinitialize current bank
    # returns the file contents/yaml string
        if bank:
            bankfile = Path(bank)
            try:
                bank = (self.bankdir / bankfile).read_text()
            except (OSError, FileNotFoundError):
                pass
            else:
                self.cfg['currentbank'] = bankfile.as_posix()
#            try:
            b = self.parse_fpyaml(bank)
#            except oyaml.YAMLError:
#                raise PatcherError("Unable to parse bank data")
#            else:
            self._bank = b
        try:
            self._bank['patches'].values()
        except:
            self._bank = {'patches': {'No Patches': {}}}
        # reinitialize the synth
        self._reset_synth_defaults()
        self._send_cc_defaults()
        if 'init' in self._bank:
            for opt, val in self._bank['init'].get('fluidsettings', {}).items():
                self.fluid_set(opt, val)
            for msg in self._bank['init'].get('cc', []):
                self._fluid.send_cc(msg.chan - 1, msg.cc, msg.val)
            for syx in self._bank['init'].get('sysex', []):
                self._parse_sysex(syx)
        self._reload_bankfonts()
        return bank

    def save_bank(self, bankfile='', raw=''):
    # save current patches, settings in :bankfile
    # if :raw parses, save it exactly
        if bankfile:
            bankfile = Path(bankfile)
        else:
            if self.currentbank == None: return
            bankfile = self.currentbank
        if raw:
            try:
                b = self.parse_fpyaml(raw)
            except (oyaml.YAMLError, IOError):
                raise PatcherError("Invalid bank data")
            else:
                self._bank = b
        else:
            raw = self.render_fpyaml(self._bank)
        (self.bankdir / bankfile).write_text(raw)
        self.cfg['currentbank'] = bankfile.as_posix()

    def select_patch(self, patch):
    # apply all the settings in :patch
        warnings = []
        self.sfpresets = []
        activechannels = []
        patch = self._resolve_patch(patch)
        
        # select soundfont presets
        for channel in range(1, self._max_channels + 1):
            self._fluid.program_unset(channel - 1)
            if channel not in patch: continue
            preset = patch[channel]
            if preset.sf not in self._soundfonts:
                self._reload_bankfonts()
            if not self._fluid.program_select(channel - 1, self.sfdir / preset.sf, preset.bank, preset.prog):
                warnings.append(f"Unable to select preset {preset} on channel {channel}")
            else:
                activechannels.append(channel)

        # activate LADSPA effects
        self._fluid.fxchain_clear()
        effects = self._bank.get('ladspafx', {})
        effects.update(**patch.get('ladspafx', {}))
        warnings.extend(self._fxchain_create(effects, set(activechannels)))
        if effects: self._fluid.fxchain_activate()

        # apply fluidsettings
        for opt, val in self._bank.get('fluidsettings', {}).items():
            self.fluid_set(opt, val)
        for opt, val in patch.get('fluidsettings', {}).items():
            self.fluid_set(opt, val)

        # add MIDI router rules
        self._fluid.router_clear()
        self._fluid.router_default()
        for rule in self._bank.get('router_rules', []) +  patch.get('router_rules', []):
            if rule == 'clear': self._fluid.router_clear()
            elif rule == 'default': self._fluid.router_default()
            else: self.add_router_rule(**rule.__dict__)

        # send CC messages
        for msg in self._bank.get('cc', []) + patch.get('cc', []):
            if msg == 'default': self._send_cc_defaults()
            else: self._fluid.send_cc(msg.chan - 1, msg.cc, msg.val)

        # send SYSEX messages
        for syx in self._bank.get('sysex', []) + patch.get('sysex', []):
            warn = self._parse_sysex(syx)
            if warn: warnings.append(warn)

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
        for channel in range(1, self._max_channels + 1):
            info = self._fluid.program_info(channel - 1)
            if not info:
                if channel in patch:
                    del patch[channel]
                continue
            sfont, bank, prog = info
            sfrel = Path(sfont).relative_to(self.sfdir).as_posix()
            patch[channel] = fpyaml.SFPreset(sfrel, bank, prog)
            cc_messages = []
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    val = self._fluid.get_cc(channel - 1, cc)
                    if val != default:
                        cc_messages.append(fpyaml.CCMsg(channel, cc, val))
        if cc_messages:
            patch['cc'] = cc_messages

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for sfont in self._soundfonts - {soundfont}:
            self._fluid.unload_soundfont(self.sfdir / sfont)
        if {soundfont} - self._soundfonts:
            if not self._fluid.load_soundfont(self.sfdir / soundfont):
                self._soundfonts = set()
                return False
        self._soundfonts = {soundfont}

        self.sfpresets = []
        for bank in range(MAX_SF_BANK):
            for prog in range(MAX_SF_PROGRAM):
                name = self._fluid.get_preset_name(self.sfdir / soundfont, bank, prog)
                if not name:
                    continue
                self.sfpresets.append(PresetInfo(name, bank, prog))
        if not self.sfpresets: return False
        for channel in range(0, self._max_channels):
            self._fluid.program_unset(channel)
        self._fluid.router_clear()
        self._fluid.router_default()
        self._fluid.fxchain_clear()
        self._reset_synth_defaults()
        self._send_cc_defaults()
        self.add_router_rule(type='note', chan=f'2-{self._max_channels + 1}=1')
        return True
        
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

    def add_router_rule(self, ruletext='', **rule):
    # translate user router rule parameters into proper
    # (min, max, mul, add) tuples for fluidsynth and
    # pass along any other parameters for extended rules
        if ruletext:
            try:
                rule = self.parse_fpyaml(ruletext)
            except (oyaml.YAMLError, IOError):
                raise PatcherError("Improperly formatted router rule")
        for par, val in rule.items():
            if isinstance(val, str):
                rule[par] = self.parse_fpyaml(val)
        chan = rule.pop('chan', None)
        if isinstance(chan, fpyaml.FromToSpec):
            for chto in range(chan.to1, chan.to2 + 1):
                rule['chan'] = fpyaml.RouterSpec(chan.from1, chan.from2, 0.0, chto)
                self.add_router_rule(**rule)
            return
        elif isinstance(chan, fpyaml.RouterSpec):
            for chfrom in range(chan.min, chan.max + 1):
                rule['chan'] = chfrom - 1, chfrom - 1, 0.0, int(chfrom * chan.mul) + chan.add - 1
                self.add_router_rule(**rule)
            return
        elif isinstance(chan, int): chan = chan - 1, chan - 1, 1.0, 0
        par1 = rule.pop('par1', None)
        if isinstance(par1, fpyaml.FromToSpec):
            par1 = par1.routerspec()
        if isinstance(par1, fpyaml.RouterSpec):
            par1 = par1.vals
        elif isinstance(par1, int): par1 = par1, par1, 1.0, 0
        par2 = rule.pop('par2', None)
        if isinstance(par2, fpyaml.FromToSpec):
            par2 = par2.routerspec()
        if isinstance(par2, fpyaml.RouterSpec):
            par2 = par2.vals
        elif isinstance(par2, int): par2 = par2, par2, 1.0, 0
        self._fluid.router_addrule(rule.pop('type'), chan, par1, par2, **rule)

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
            if patch < 0 or patch >= len(self._bank['patches']):
                raise PatcherError("Patch index out of range")
            name = list(self._bank['patches'])[patch]
            patch = self._bank['patches'][name]
        elif isinstance(patch, str):
            name = patch
            if name not in self._bank['patches']:
                raise PatcherError(f"Patch not found: {name}")
            patch = self._bank['patches'][name]
        return patch

    def _fxchain_create(self, fxchain, activechannels):
        warnings = {}
        for hostports, midichannels in self._fluid.hostports_mapping:
            lastports = list(hostports)
            for name, fx in fxchain.items():
                chan = fx.get('chan', None)
                if isinstance(chan, fpyaml.FromToSpec):
                    fxchannels = set(range(chan.min, chan.max + 1))
                elif isinstance(chan, list):
                    fxchannels = set(chan)
                elif isinstance(chan, int):
                    fxchannels = {chan}
                else:
                    fxchannels = set(range(1, self._max_channels + 1))
                if not midichannels & fxchannels & activechannels:
                    continue
                audio = fx.get('audio', 'stereo')
                if audio == 'stereo':
                    audio = 'Input L', 'Input R', 'Output L', 'Output R'
                elif audio == 'mono':
                    audio = 'Input', 'Output'
                if len(audio) == 4:
                    inports, outports = (audio[0], audio[1]), (audio[2], audio[3])
                    fxpair = [self._fluid.fxunit_add(name, self.plugindir / fx['lib'], fx.get('plugin', None))] * 2
                elif len(audio) == 2:
                    inports, outports = (audio[0], audio[0]), (audio[1], audio[1])
                    fxpair = [self._fluid.fxunit_add(name, self.plugindir / fx['lib'], fx.get('plugin', None)),
                              self._fluid.fxunit_add(name, self.plugindir / fx['lib'], fx.get('plugin', None))]
                if any([x == None for x in fxpair]):
                    warnings[name] = f"Could not connect LADSPA plugin {name}"
                    continue
                for x, y, z in zip(fxpair, inports, lastports[-2:]):
                    self._fluid.fxchain_link(x, y, z)
                if name != list(fxchain)[-1]:
                    for x, y in zip(fxpair, outports):
                        lastports.append(self._fluid.fxbuffer_add())
                        self._fluid.fxchain_link(x, y, lastports[-1])
                else:
                    for x, y, z in zip(fxpair, outports, hostports):
                        self._fluid.fxchain_link(x, y, z)
                if 'mix' in fx:
                    self._fluid.fx_setmix(name, fx['mix'])
                if 'vals' in fx:
                    for ctrl, val in fx['vals'].items():
                        self._fluid.fx_setcontrol(name, ctrl, val)
        return list(warnings.values())

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

    def _send_cc_defaults(self, channels=[]):
        for channel in channels or range(1, self._max_channels + 1):
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    self._fluid.send_cc(channel - 1, cc, default)
        
    def _reset_synth_defaults(self):
        cfg_fset = self.cfg.get('fluidsettings', {})
        for opt, val in SYNTH_DEFAULTS.items():
            if opt in cfg_fset:
                self.fluid_set(opt, cfg_fset[opt])
            else:
                self.fluid_set(opt, val)
        
