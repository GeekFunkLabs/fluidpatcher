"""
Copyright (c) 2020 Bill Peterson

Description: a performance-oriented patch interface for fluidsynth
"""
import re, mido
from copy import deepcopy
from os.path import relpath, join as joinpath
from . import yamlext, cclink, fluidwrap

MAX_SF_BANK = 129
MAX_SF_PROGRAM = 128

CC_DEFAULTS = [(7, 7, 100), (11, 11, 127), (12, 31, 0), (33, 42, 0),
               (43, 43, 127), (44, 63, 0), (65, 65, 0), (70, 79, 64),
               (80, 83, 0), (84, 84, 255), (85, 95, 0), (102, 119, 0)]
               
VERSION = '0.4.1'

def read_yaml(text):
    if '---' in text:
        return yamlext.safe_load_all(text)
    return yamlext.safe_load(text)

def write_yaml(*args):
    if len(args) > 1:
        return yamlext.safe_dump_all(args)
    return yamlext.safe_dump(args[0])

class PatcherError(Exception):
    pass

class Patcher:

    def __init__(self, cfgfile='', fluidsettings={}):
        self._cfgfile = cfgfile
        self.cfg = {}
        self.read_config()
        fluidsettings.update(self.cfg.get('fluidsettings', {}))
        self._fluid = fluidwrap.Synth(**fluidsettings)        
        self._max_channels = fluidsettings.get('synth.midi-channels', 16)
        self._bank = {'patches': {'No Patches': {}}}
        self._soundfonts = set()
        self._cc_links = []
        self.sfpresets = []

    @property
    def cfgfile(self):
        return self._cfgfile
        
    @property
    def sfdir(self):
        return self.cfg.get('soundfontdir', 'sf2')
        
    @property
    def bankdir(self):
        return self.cfg.get('bankdir', 'banks')
        
    @property
    def plugindir(self):
        return self.cfg.get('plugindir', '')
        
    @property
    def currentbank(self):
        return self.cfg.get('currentbank', '')

    def read_config(self):
        if self._cfgfile == '':
            return write_yaml(self.cfg)
        f = open(self._cfgfile)
        raw = f.read()
        f.close()
        try:
            self.cfg = read_yaml(raw)
        except (yamlext.YAMLError, IOError):
            raise PatcherError("Bad configuration file")
        return raw

    def write_config(self, raw=None):
        if self._cfgfile == '':
            return
        f = open(self._cfgfile, 'w')
        if raw:
            try:
                c = read_yaml(raw)
            except (yamlext.YAMLError, IOError):
                raise PatcherError("Invalid config data")
            self.cfg = c
            f.write(raw)
        else:
            f.write(write_yaml(self.cfg))
        f.close()

    def load_bank(self, bank=None):
    # load patches, settings from :bank yaml string or filename
    # returns the file contents/yaml string
        if bank == None:
            bfile = self.currentbank
        else:
            bfile = bank
        try:
            f = open(joinpath(self.bankdir, bfile))
            bank = f.read()
            f.close()
            self.cfg['currentbank'] = bfile
        except (OSError, FileNotFoundError):
            pass
        try:
            b = read_yaml(bank)
        except yamlext.YAMLError:
            raise PatcherError("Unable to parse bank data")
        self._bank = b
        try:
            self._bank['patches'].values()
        except:
            self._bank = {'patches': {'No Patches': {}}}

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
        if not bankfile:
            bankfile = self.currentbank
        f = open(joinpath(self.bankdir, bankfile), 'w')
        if raw:
            try:
                b = read_yaml(raw)
            except (yamlext.YAMLError, IOError):
                raise PatcherError("Invalid bank data")
            self._bank = b
            f.write(raw)
        else:
            f.write(write_yaml(self._bank))
        f.close()
        self.cfg['currentbank'] = bankfile

    def patch_name(self, patch_index):
        if patch_index >= len(self._bank['patches']):
            raise PatcherError("Patch index out of range")
        return list(self._bank['patches'])[patch_index]
        
    def patch_names(self):
        return list(self._bank['patches'])
        
    def patch_index(self, patch_name):
        if patch_name not in self._bank['patches']:
            raise PatcherError("Patch not found: %s" % patch_name)
        return list(self._bank['patches']).index(patch_name)

    def patches_count(self):
        return len(self._bank['patches'])

    def select_patch(self, patch):
    # select :patch by index, name, or passing dict object
        warnings = []
        self.sfpresets = []
        patch = self._resolve_patch(patch)
        
        # select soundfont presets
        for channel in range(1, self._max_channels + 1):
            self._fluid.program_unset(channel - 1)
            if channel not in patch: continue
            preset = patch[channel]
            if preset.name not in self._soundfonts:
                self._reload_bankfonts()
            if not self._fluid.program_select(channel - 1, joinpath(self.sfdir, preset.name), preset.bank, preset.prog):
                warnings.append('Unable to select preset %s on channel %d' % (preset, channel))

        # link CC messages to parameters
        for type in ['effect', 'fluidsetting']:
            self.cclinks_clear(type)
        for link in self._bank.get('cclinks', []) + patch.get('cclinks', []):
            self.link_cc(**link.__dict__)

        # activate LADSPA effects
        self._fluid.fxchain_clear()
        n = 1
        for effect in self._bank.get('effects', []) + patch.get('effects', []):
            name = 'e%s' % n
            warn = self._fxplugin_connect(name, **effect)
            if warn: warnings.append(warn)
            else: n += 1
        if n > 1: self._fluid.fxchain_activate()

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
            else:
                self._midi_route(**rule.__dict__)

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
                    self._bank['patches'][name][x] = deepcopy(addlike[x])
        return(self._bank['patches'][name])

    def delete_patch(self, patch):
        if isinstance(patch, int):
            name = list(self._bank['patches'])[patch]
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
            patch[channel] = yamlext.SFPreset(relpath(sfont, start=self.sfdir), bank, prog)
            cc_messages = []
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    val = self._fluid.get_cc(channel - 1, cc)
                    if val != default:
                        cc_messages.append(yamlext.CCMsg(channel, cc, val))
        if cc_messages:
            patch['cc'] = cc_messages

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for sfont in self._soundfonts - {soundfont}:
            self._fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        if {soundfont} - self._soundfonts:
            if not self._fluid.load_soundfont(joinpath(self.sfdir, soundfont)):
                self._soundfonts = set()
                return False
        self._soundfonts = {soundfont}

        self.sfpresets = []
        for bank in range(MAX_SF_BANK):
            for prog in range(MAX_SF_PROGRAM):
                name = self._fluid.get_preset_name(joinpath(self.sfdir, soundfont), bank, prog)
                if not name:
                    continue
                self.sfpresets.append(yamlext.SFPreset(name, bank, prog))
        if not self.sfpresets: return False
        for channel in range(0, self._max_channels):
            self._fluid.program_unset(channel)
        self._fluid.router_clear()
        self._fluid.router_default()
        self._fluid.fxchain_clear()
        self._send_cc_defaults()
        self._midi_route('note', chan=yamlext.FromToSpec(2, self._max_channels, 0, 0))
        return True
        
    def select_sfpreset(self, presetnum):
        warnings = []
        if presetnum < len(self.sfpresets):
            p = self.sfpresets[presetnum]
            soundfont = list(self._soundfonts)[0]
            if not self._fluid.program_select(0, joinpath(self.sfdir, soundfont), p.bank, p.prog):
                warnings.append('Unable to select preset %s' % p)
        else:
            warnings.append('Preset out of range')
        return warnings

    def fluid_get(self, opt):
        return self._fluid.get_setting(opt)

    def fluid_set(self, opt, val, updatebank=False, patch=None):
        self._fluid.setting(opt, val)
        if updatebank:
            self._bank['fluidsettings'][opt] = val
            if patch:
                patch = self._resolve_patch(patch)
                if opt in patch.get('fluidsettings', {}):
                    patch['fluidsettings'].remove(opt)

    def link_cc(self, target, link='', type='fluidsetting', xfrm=yamlext.RouterSpec(0, 127, 1, 0), **kwargs):
        if 'chan' in kwargs:
            link = '%s/%s' % (kwargs['chan'], kwargs['cc'])
        if not isinstance(xfrm, yamlext.YAMLObject):
            try:
                xfrm = read_yaml(xfrm)
            except yamlext.YAMLError:
                raise PatcherError("Badly formatted xfrm for CCLink")
        if isinstance(xfrm, yamlext.FromToSpec):
            xfrm = yamlext.RouterSpec.fromtospec(xfrm)        
        self._cc_links.append(cclink.CCLink(self._fluid, target, link, type, xfrm, **kwargs))
                
    def poll_cc(self):
        retvals = {}
        for link in self._cc_links:
            if link.haschanged():
                if link.xfrm.min <= link.val <= link.xfrm.max:
                    val = link.val * link.xfrm.mul + link.xfrm.add
                    if link.type == 'fluidsetting':
                        self.fluid_set(link.target, val)
                    elif link.type == 'effect':
                        self._fluid.fx_setcontrol(link.target, link.port, val)
                    else:
                        retvals[link.target] = val
        return retvals
        
    def cclinks_clear(self, type=''):
        if type:
            self._cc_links = [link for link in self._cc_links if link.type != type]
        else:
            self._cc_links = []
        
    # private functions
    def _reload_bankfonts(self):
        sfneeded = set()
        for patch in self._bank['patches'].values():
            for channel in patch:
                if isinstance(channel, int):
                    sfneeded |= {patch[channel].name}
        missing = set()
        for sfont in self._soundfonts - sfneeded:
            self._fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        for sfont in sfneeded - self._soundfonts:
            if not self._fluid.load_soundfont(joinpath(self.sfdir, sfont)):
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
                raise PatcherError("Patch not found: %s" % name)
            patch = self._bank['patches'][name]
        return patch
        
    def _parse_sysex(self, messages):
        ports = {}
        try:
            for msg in messages:
                if msg[0] not in ports:
                    ports[msg[0]] = mido.open_output(msg[0])
                if isinstance(msg[1], int):
                    messages = [msg[1:]]
                else:
                    messages = mido.read_syx_file(msg[1])
                for msgdata in messages:
                    ports[msg[0]].send(mido.Message('sysex', data = msgdata))
            for x in ports.keys():
                ports[x].close()
        except:
            return "Failed to parse or send SYSEX"

    def _fxplugin_connect(self, name, lib, plugin=None, audioports='stereo', controls=[]):
        libpath = joinpath(self.plugindir, lib)
        if audioports == 'mono':
            audioports = ('Input', 'Output')
        elif audioports == 'stereo':
            audioports = ('Input L', 'Input R', 'Output L', 'Output R')

        if len(audioports) == 4:
            names = (name, )
        elif len(audioports) == 2:
            names = (name + 'L', name + 'R')
        for x in names:
            if not self._fluid.fxchain_add(x, libpath, plugin):
                return "Could not connect plugin %s" % lib
            for ctrl in controls:
                if hasattr(ctrl, 'val'):
                    self._fluid.fx_setcontrol(x, ctrl.port, ctrl.val)
                if hasattr(ctrl, 'link'):
                    self.link_cc(x, type='effect', **ctrl.__dict__)

        if len(names) == 1:
            self._fluid.fxchain_link(names[0], audioports[0], 'Main:L')
            self._fluid.fxchain_link(names[0], audioports[2], 'Main:L')
            self._fluid.fxchain_link(names[0], audioports[1], 'Main:R')
            self._fluid.fxchain_link(names[0], audioports[3], 'Main:R')
        elif len(names) == 2:
            self._fluid.fxchain_link(names[0], audioports[0], 'Main:L')
            self._fluid.fxchain_link(names[0], audioports[1], 'Main:L')
            self._fluid.fxchain_link(names[1], audioports[0], 'Main:R')
            self._fluid.fxchain_link(names[1], audioports[1], 'Main:R')

    def _midi_route(self, type, chan=None, par1=None, par2=None, **kwargs):
    # send midi message routing rules to fluidsynth
        if isinstance(chan, yamlext.FromToSpec):
            for chto in range(chan.to1, chan.to2 + 1):
                ch = yamlext.RouterSpec(chan.from1, chan.from2, 0, chto)
                self._midi_route(type, ch, par1, par2, **kwargs)
            return
        if isinstance(chan, yamlext.RouterSpec):
            for chfrom in range(chan.min, chan.max + 1):
                ch = [chfrom - 1, chfrom - 1, 0, chfrom * chan.mul + chan.add - 1]
                self._midi_route(type, ch, par1, par2)
            return
        if isinstance(par1, yamlext.FromToSpec):
            if type == 'cc':
                for ccto in range(par1.to1, par1.to2 + 1):
                    p = yamlext.RouterSpec(par1.from1, par1.from2, 0, ccto)
                    self._midi_route(type, chan, p, par2, **kwargs)
                return
            else:
                par1 = yamlext.RouterSpec.fromtospec(par1)
        if isinstance(par1, yamlext.RouterSpec):
            par1 = par1.vals
        if isinstance(par2, yamlext.FromToSpec):
            par2 = yamlext.RouterSpec.fromtospec(par2)
        if isinstance(par2, yamlext.RouterSpec):
            par2 = par2.vals
        self._fluid.router_addrule(type, chan, par1, par2)

    def _send_cc_defaults(self, channels=[]):
        for channel in channels or range(1, self._max_channels + 1):
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    self._fluid.send_cc(channel - 1, cc, default)
        
