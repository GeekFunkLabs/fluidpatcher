"""
Copyright (c) 2020 Bill Peterson

Description: a performance-oriented patch interface for fluidsynth
"""
import re, mido
from copy import deepcopy
from os.path import join as joinpath
from . import yamlext, cclink, fluidwrap

MAX_BANK = 129
MAX_PRESET = 128

CC_DEFAULTS = [(7, 7, 100), (11, 11, 127), (12, 31, 0), (33, 42, 0),
               (43, 43, 127), (44, 63, 0), (65, 65, 0), (70, 79, 64),
               (80, 83, 0), (84, 84, 255), (85, 95, 0), (102, 119, 0)]

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

    def __init__(self, cfgfile=''):
        self.cfgfile = cfgfile
        if self.cfgfile != '':
            try:
                f = open(self.cfgfile)
                self.cfg = read_yaml(f.read())
            except yamlext.YAMLError or IOError:
                raise PatcherError("Bad configuration file")
            f.close()
        else:
            self.cfg = {'currentbank': ''}
            
        self.sfdir = self.cfg.get('soundfontdir', 'sf2')
        self.bankdir = self.cfg.get('bankdir', 'banks')
        self.plugindir = self.cfg.get('plugindir', '')
        fluidsettings = self.cfg.get('fluidsettings', {})

        self.fluid = fluidwrap.Synth(**fluidsettings)
        self.max_channels = fluidsettings.get('synth.midi-channels', 16)

        self.bank = None
        self.soundfonts = set()
        self.sfpresets = []
        self.cc_links = []

    def write_config(self, raw=''):
        if self.cfgfile == '':
            return
        f = open(self.cfgfile, 'w')
        if raw:
            try:
                c = read_yaml(raw)
            except yamlext.YAMLError or IOError:
                raise PatcherError("Invalid bank data")
            self.cfg = c
            f.write(raw)
        else:
            f.write(write_yaml(self.cfg))
        f.close()

    def load_bank(self, bank=''):
    # load patches, settings from :bank yaml string or filename
        if '\n' in bank:
            try:
                b = read_yaml(bank)
            except yamlext.YAMLError:
                raise PatcherError("Unable to parse bank data")
            self.cfg['currentbank'] = ''
        else:
            if bank == '':
                bank = self.cfg['currentbank']
            f = open(joinpath(self.bankdir, bank))
            try:
                b = read_yaml(f.read())
            except yamlext.YAMLError:
                raise PatcherError("Unable to load bank")
            f.close()
            self.cfg['currentbank'] = bank
            
        self.bank = b

        if 'fluidsettings' in self.bank:
            for opt, val in self.bank['fluidsettings'].items():
                self.fluid_set(opt, val)
        self._reload_bankfonts()

    def save_bank(self, bankfile='', raw=''):
    # save current patches, settings in :bankfile
    # if :raw parses, save it exactly
        if not bankfile:
            bankfile = self.cfg['currentbank']
        f = open(joinpath(self.bankdir, bankfile), 'w')
        if raw:
            try:
                b = read_yaml(raw)
            except yamlext.YAMLError or IOError:
                raise PatcherError("Invalid bank data")
            self.bank = b
            f.write(raw)
        else:
            f.write(write_yaml(self.bank))
        f.close()
        self.cfg['currentbank'] = bankfile

    def patch_name(self, patch_index=-1):
        if patch_index >= len(self.bank['patches']):
            raise PatcherError("Patch index out of range")
        if patch_index == -1:
            return list(self.bank['patches'])
        return list(self.bank['patches'])[patch_index]
        
    def patch_index(self, patch_name):
        if patch_name not in self.bank['patches']:
            raise PatcherError("Patch not found: %s" % patch_name)
        return list(self.bank['patches']).index(patch_name)

    def patches_count(self):
        return len(self.bank['patches'])

    def select_patch(self, patch):
    # select :patch by index, name, or passing dict object
        warnings = []
        self.sfpresets = []
        patch = self._resolve_patch(patch)
        for channel in range(1, self.max_channels + 1):
            if channel in patch:
                if patch[channel].name not in self.soundfonts:
                    self._reload_bankfonts()
                if not self.fluid.program_select(channel - 1,
                                                 joinpath(self.sfdir, patch[channel].name),
                                                 patch[channel].bank,
                                                 patch[channel].prog):
                    self.fluid.program_unset(channel - 1)
                    warnings.append('Unable to set channel %d' % channel)
            else:
                self.fluid.program_unset(channel - 1)

        for msg in self.bank.get('cc', []) + patch.get('cc', []):
            self.fluid.send_cc(msg.chan - 1, msg.cc, msg.val)

        for syx in self.bank.get('sysex', []) + patch.get('sysex', []):
            warn = self._parse_sysex(syx)
            if warn: warnings.append(warn)

        for type in ['effect', 'fluidsetting']:
            self.cclinks_clear(type)
        for link in self.bank.get('cclinks', []) + patch.get('cclinks', []):
            self.link_cc(**link.dict())

        self.fluid.fxchain_clear()
        fx = self.bank.get('effects', []) + patch.get('effects', [])
        n = 1
        for effect in fx:
            name = 'e%s' % n
            warn = self._fxplugin_connect(name, **effect)
            if warn:
                warnings.append(warn)
            else:
                n += 1
        if n > 1:
            self.fluid.fxchain_activate()

        self.fluid.router_clear()
        for rule in self.bank.get('router_rules', []):
            self._midi_route(**rule.dict())
        for rule in patch.get('router_rules', []):
            if rule == 'default':
                self.fluid.router_default()
            elif rule == 'clear':
                self.fluid.router_clear()
            else:
                self._midi_route(**rule.dict())
        if 'rule' not in locals():
            self.fluid.router_default()

        if warnings:
            return warnings

    def add_patch(self, name, addlike=None):
    # new empty patch name :name, copying settings from :addlike
        self.bank['patches'][name] = {}
        if addlike:
            addlike = self._resolve_patch(addlike)
            if 'router_rules' in addlike:
                self.bank['patches'][name]['router_rules'] = deepcopy(addlike['router_rules'])
            if 'cc' in addlike:
                self.bank['patches'][name]['cc'] = deepcopy(addlike['cc'])
            if 'sysex' in addlike:
                self.bank['patches'][name]['sysex'] = deepcopy(addlike['sysex'])
        return(self.bank['patches'][name])

    def delete_patch(self, patch):
        if isinstance(patch, int):
            name = list(self.bank['patches'])[patch]
        else:
            name = patch
        del self.bank['patches'][name]
        self._reload_bankfonts()

    def update_patch(self, patch):
    # update :patch in current bank with fluidsynth's present state
        patch = self._resolve_patch(patch)
        for channel in range(1, self.max_channels + 1):
            info = self.fluid.program_info(channel - 1)
            if not info:
                if channel in patch:
                    del patch[channel]
                continue
            sfont, bank, prog = info
            patch[channel] = yamlext.SFPreset(sfont, bank, prog)
            cc_messages = []
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    val = self.fluid.get_cc(channel - 1, cc)
                    if val != default:
                        cc_messages.append(yamlext.CCMsg(channel, cc, val))
        if cc_messages:
            patch['cc'] = cc_messages

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for sfont in self.soundfonts - {soundfont}:
            self.fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        if {soundfont} - self.soundfonts:
            if not self.fluid.load_soundfont(joinpath(self.sfdir, soundfont)):
                self.soundfonts = set()
                return False
        self.soundfonts = {soundfont}

        self.sfpresets = []
        for bank in range(MAX_BANK):
            for prog in range(MAX_PRESET):
                name = self.fluid.get_preset_name(joinpath(self.sfdir, soundfont), bank, prog)
                if not name:
                    continue
                self.sfpresets.append(yamlext.SFPreset(name, bank, prog))
        if not self.sfpresets: return False
        return True
        
    def select_sfpreset(self, presetnum):
        p = self.sfpresets[presetnum]
        if not self.soundfonts:
            return False
        soundfont = list(self.soundfonts)[0]
        if not self.fluid.program_select(0, joinpath(self.sfdir, soundfont), p.bank, p.prog):
            return False
        for channel in range(1, self.max_channels + 1):
            self.fluid.program_unset(channel)
        self.fluid.router_clear()
        self.fluid.router_default()
        return True                
        
    def fluid_get(self, opt):
        return self.fluid.get_setting(opt)

    def fluid_set(self, opt, val, updatebank=False):
        self.fluid.setting(opt, val)
        if updatebank:
            self.bank['fluidsettings'][opt] = val

    def link_cc(self, target, link='', type='fluidsetting', xfrm=yamlext.RouterSpec(0, 127, 1, 0), **kwargs):
        if 'chan' in kwargs:
            link = '%s/%s' % (kwargs['chan'], kwargs['cc'])
        if not isinstance(xfrm, yamlext.RouterSpec):
            try:
                xfrm = read_yaml(xfrm)
            except yamlext.YAMLError:
                raise PatcherError("Badly formatted xfrm for CCLink")
        self.cc_links.append(cclink.CCLink(self.fluid, target, link, type, xfrm, **kwargs))
                
    def poll_cc(self):
        retvals = {}
        for link in self.cc_links:
            if link.haschanged():
                if link.type == 'patch':
                    if link.val > 0:
                        if link.target == 'inc':
                            retvals['patch'] = 1
                        elif link.target == 'dec':
                            retvals['patch'] = -1
                elif link.xfrm.min <= link.val <= link.xfrm.max:
                    val = link.val * link.xfrm.mul + link.xfrm.add
                    if link.type == 'effect':
                        self.fluid.fx_setcontrol(link.target, link.port, val)
                    elif link.type == 'fluidsetting':
                        self.fluid_set(link.target, val)
        return retvals
        
    def cclinks_clear(self, type=''):
        for link in self.cc_links:
            if type == '' or link.type == type:
                self.cc_links.remove(link)
        
    # private functions
    def _reload_bankfonts(self):
        sfneeded = set()
        for patch in self.bank['patches'].values():
            for channel in patch:
                if isinstance(channel, int):
                    sfneeded |= {patch[channel].name}
        missing = set()
        for sfont in self.soundfonts - sfneeded:
            self.fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        for sfont in sfneeded - self.soundfonts:
            if not self.fluid.load_soundfont(joinpath(self.sfdir, sfont)):
                missing |= {sfont}
        self.soundfonts = sfneeded - missing

    def _resolve_patch(self, patch):
        if isinstance(patch, int):
            if patch < 0 or patch >= len(self.bank['patches']):
                raise PatcherError("Patch index out of range")
            name = list(self.bank['patches'])[patch]
            patch = self.bank['patches'][name]
        elif isinstance(patch, str):
            name = patch
            if name not in self.bank['patches']:
                raise PatcherError("Patch not found: %s" % name)
            patch = self.bank['patches'][name]
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
            if not self.fluid.fxchain_add(x, libpath, plugin):
                return "Could not connect plugin %s" % lib
            for ctrl in controls:
                if hasattr(ctrl, 'val'):
                    self.fluid.fx_setcontrol(x, ctrl.port, ctrl.val)
                if hasattr(ctrl, 'link'):
                    self.link_cc(x, type='effect', **ctrl.dict())

        if len(names) == 1:
            self.fluid.fxchain_link(name[0], audioports[0], 'Main:L')
            self.fluid.fxchain_link(name[0], audioports[2], 'Main:L')
            self.fluid.fxchain_link(name[0], audioports[1], 'Main:R')
            self.fluid.fxchain_link(name[0], audioports[3], 'Main:R')
        elif len(names) == 2:
            self.fluid.fxchain_link(name[0], audioports[0], 'Main:L')
            self.fluid.fxchain_link(name[0], audioports[1], 'Main:L')
            self.fluid.fxchain_link(name[1], audioports[0], 'Main:R')
            self.fluid.fxchain_link(name[1], audioports[1], 'Main:R')

    def _midi_route(self, type, chan=None, par1=None, par2=None, **kwargs):
    # send midi message routing rules to fluidsynth
    # convert scientific note names in :par1 to midi note numbers
        par1_list = None
        if par1:
            par1_list = []
            for a in ['min', 'max', 'mul', 'add']:
                val = getattr(par1, a)
                if isinstance(val, str):
                    sci = re.findall('([+-]?)([A-G])([b#]?)([0-9])', val)[0]
                    sign = ('+ -'.find(sci[0]) - 1) * -1
                    note = 'C_D_EF_G_A_B'.find(sci[1])
                    sharpflat = (' #b'.find(sci[2]) + 1) % 3 - 1
                    octave = int(sci[3])
                    par1_list.append(sign * (octave * 12 + note + sharpflat))
                else:
                    par1_list.append(val)
        par2_list = None
        if par2:
            par2_list = [par2.min, par2.max, par2.mul, par2.add]
        if isinstance(chan, yamlext.FromToSpec):
            for chfrom in range(chan.from1, chan.from2 + 1):
                for chto in range(chan.to1, chan.to2 + 1):
                    chan_list = [chfrom - 1, chfrom - 1, 0, chto - 1]
                    self.fluid.router_addrule(type, chan_list, par1_list, par2_list)
        elif isinstance(chan, yamlext.RouterSpec):
            for chfrom in range(chan.min, chan.max + 1):
                chan_list = [chfrom - 1, chfrom - 1, 0, chfrom * chan.mul + chan.add - 1]
                self.fluid.router_addrule(type, chan_list, par1_list, par2_list)
        else:
            self.fluid.router_addrule(type, None, par1_list, par2_list)

