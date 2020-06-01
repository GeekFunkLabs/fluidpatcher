"""
Copyright (c) 2020 Bill Peterson

Description: a performance-oriented patch interface for fluidsynth
"""
import re, oyaml, mido
from copy import deepcopy
from os.path import join as joinpath
import fluidwrap

MAX_BANK = 129
MAX_PRESET = 128

CC_DEFAULTS = [(7, 7, 100), (11, 11, 127), (12, 31, 0), (33, 42, 0),
               (43, 43, 127), (44, 63, 0), (65, 65, 0), (70, 79, 64),
               (80, 83, 0), (84, 84, 255), (85, 95, 0), (102, 119, 0)]
               
class SFPreset(oyaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper

    def __init__(self, sfont, bank, prog):
        self.sfont = sfont
        self.bank = bank
        self.prog = prog

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar('!sfpreset', '%s:%03d:%03d' % (data.sfont, data.bank, data.prog))

    @classmethod
    def from_yaml(cls, loader, node):
        vals = loader.construct_scalar(node).split(':')
        sfont = vals[0]
        bank = int(vals[1])
        prog = int(vals[2])
        return SFPreset(sfont, bank, prog)

oyaml.add_implicit_resolver('!sfpreset', re.compile('^[^:]+:\d+:\d+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class CCMsg(oyaml.YAMLObject):

    yaml_tag = '!ccmsg'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper

    def __init__(self, chan, cc, val):
        self.chan = chan
        self.cc = cc
        self.val = val

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar('!ccmsg', '%d/%d=%d' % (data.chan, data.cc, data.val))

    @classmethod
    def from_yaml(cls, loader, node):
        msg = re.findall('[^/=]+', loader.construct_scalar(node))
        chan, cc, val = map(int, msg)
        return CCMsg(chan, cc, val)

oyaml.add_implicit_resolver('!ccmsg', re.compile('^[0-9]+/[0-9]+=[0-9]+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class RouterSpec(oyaml.YAMLObject):

    yaml_tag = '!rspec'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper
    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add
    @classmethod
    def to_yaml(cls, dumper, data):
        if isinstance(data.add, int):
            rep = '%s-%s*%s%+d' % (data.min, data.max, data.mul, data.add)
        else:
            rep = '%s-%s*%s%s' % (data.min, data.max, data.mul, data.add)
        return dumper.represent_scalar('!rspec', rep)
    @classmethod
    def from_yaml(cls, loader, node):
        patt = '^([\dA-Gb#]+)-([\dA-Gb#]+)\*(-?[\d\.]+)([+-][\dA-Gb#]+)$'
        route = list(re.findall(patt, loader.construct_scalar(node))[0])
        for i, spec in enumerate(route):
            if re.match('^[+-]?(\d*\.\d+|\d+\.\d*)', spec):
                route[i] = float(spec)
            elif re.match('^[+-]?[\d]+', spec):
                route[i] = int(spec)
        return RouterSpec(*route)
oyaml.add_implicit_resolver('!rspec', re.compile('^[\dA-Gb#]+-[\dA-Gb#]+\*-?[\d\.]+[+-][\dA-Gb#]+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class FromToSpec(oyaml.YAMLObject):

    yaml_tag = '!ftspec'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper
    def __init__(self, from1, from2, to1, to2):
        self.from1 = from1
        self.from2 = from2
        self.to1 = to1
        self.to2 = to2
    @classmethod
    def to_yaml(cls, dumper, data):
        rep = '%d-%d>%d-%d' % (data.from1, data.from2, data.to1, data.to2)
        return dumper.represent_scalar('!ftspec', rep)
    @classmethod
    def from_yaml(cls, loader, node):
        spec = re.findall('[^->]+', loader.construct_scalar(node))
        from1, from2, to1, to2 = map(int, spec)
        return FromToSpec(from1, from2, to1, to2)
oyaml.add_implicit_resolver('!ftspec', re.compile('^\d+-\d+\>\d+-\d+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class FlowSeq(oyaml.YAMLObject):

    yaml_tag = '!flowseq'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper

    def __init__(self, items):
        self.items=items

    def __iter__(self):
        return iter(self.items)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_sequence('!flowseq', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return FlowSeq(loader.construct_sequence(node))

class FlowMap(oyaml.YAMLObject):

    yaml_tag = '!flowmap'
    yaml_loader=oyaml.SafeLoader
    yaml_dumper=oyaml.SafeDumper
    
    def __init__(self, **kwargs):
        for a in kwargs:
            setattr(self, a, kwargs[a])

    def __iter__(self):
        return iter(self.__dict__.items())

    def dict(self):
        return self.__dict__

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping('!flowmap', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return FlowMap(**loader.construct_mapping(node))

oyaml.add_path_resolver('!flowseq',
                        [(oyaml.MappingNode, None),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'cc')], 
                        kind=list, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'router_rules'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, None),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'router_rules'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

def read_yaml(stream):
    return oyaml.safe_load(stream)

def write_yaml(data, stream=None):
    return oyaml.safe_dump(data, stream)

class PatcherError(Exception):
    pass

class Patcher:

    def __init__(self, cfgfile=''):
        self.cfgfile = cfgfile
        if cfgfile != '':
            try:
                f = open(self.cfgfile)
                self.cfg = read_yaml(f)
            except oyaml.YAMLError or IOError:
                raise PatcherError("Bad configuration file")
            f.close()
        else:
            self.cfg = {'currentbank': ''}
            
        self.sfdir = self.cfg.get('soundfontdir', 'sf2')
        self.bankdir = self.cfg.get('bankdir', 'banks')
        fluidsettings = self.cfg.get('fluidsettings', {})

        self.fluid = fluidwrap.Synth(**fluidsettings)
        self.max_channels = fluidsettings.get('synth.midi-channels', 16)

        self.bank = None
        self.soundfonts = set()
        self.sfpresets = []

    def write_config(self):
        if self.cfgfile == '':
            return
        f = open(self.cfgfile, 'w')
        try:
            write_yaml(self.cfg, f)
        except oyaml.YAMLError or IOError:
            raise PatcherError("Error writing configuration")
        f.close()

    def load_bank(self, bank=''):
    # load patches, settings from :bank yaml string or filename
        if '\n' in bank:
            try:
                b = read_yaml(bank)
            except oyaml.YAMLError:
                raise PatcherError("Unable to parse bank data")
            self.cfg['currentbank'] = ''
        else:
            if bank == '':
                bank = self.cfg['currentbank']
            f = open(joinpath(self.bankdir, bank))
            try:
                b = read_yaml(f)
            except oyaml.YAMLError:
                raise PatcherError("Unable to load bank")
            f.close()
            self.cfg['currentbank'] = bank
            
        self.bank = b

        if 'fluidsettings' in self.bank:
            for opt, val in self.bank['fluidsettings'].items():
                self.fluid.setting(opt, val)

    def _reload_bankfonts(self):
        sfneeded = set()
        for patch in self.bank['patches'].values():
            for channel in patch:
                if isinstance(channel, int):
                    sfneeded |= {patch[channel].sfont}
        missing = set()
        for sfont in self.soundfonts - sfneeded:
            self.fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        for sfont in sfneeded - self.soundfonts:
            if not self.fluid.load_soundfont(joinpath(self.sfdir, sfont)):
                missing |= {sfont}
        self.soundfonts = sfneeded - missing

    def save_bank(self, bankfile='', raw=''):
    # save current patches, settings in :bankfile
    # if :raw parses, save it exactly
        if not bankfile:
            bankfile = self.cfg['currentbank']
        f = open(joinpath(self.bankdir, bankfile), 'w')
        if raw:
            try:
                b = read_yaml(raw)
            except oyaml.YAMLError or IOError:
                raise PatcherError("Invalid bank data")
            self.bank = b
            f.write(raw)
        else:
            write_yaml(self.bank, f)
        f.close()
        self.cfg['currentbank'] = bankfile

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
        
    def patch_name(self, patch_index):
        if patch_index < 0 or patch_index >= len(self.bank['patches']):
            raise PatcherError("Patch index out of range")
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
                if patch[channel].sfont not in self.soundfonts:
                    self._reload_bankfonts()
                if not self.fluid.program_select(channel - 1,
                                                 joinpath(self.sfdir, patch[channel].sfont),
                                                 patch[channel].bank,
                                                 patch[channel].prog):
                    self.fluid.program_unset(channel - 1)
                    warnings.append('Unable to set channel %d' % channel)
            else:
                self.fluid.program_unset(channel - 1)
        if 'cc' in patch:
            for msg in patch['cc']:
                self.fluid.send_cc(msg.chan - 1, msg.cc, msg.val)
        if 'sysex' in patch:
            ports = {}
            try:
                for msg in patch['sysex']:
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
                warnings.append("Failed to parse or send SYSEX")

        self.fluid.router_clear()
        if 'router_rules' in self.bank:
            for rule in self.bank['router_rules']:
                self._midi_route(**rule.dict())
        if 'router_rules' in patch:
            for rule in patch['router_rules']:
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
            patch[channel] = SFPreset(sfont, bank, prog)
            cc_messages = []
            for first, last, default in CC_DEFAULTS:
                for cc in range(first, last + 1):
                    val = self.fluid.get_cc(channel - 1, cc)
                    if val != default:
                        cc_messages.append(CCMsg(channel, cc, val))
        if cc_messages:
            patch['cc'] = cc_messages

    def load_soundfont(self, soundfont):
    # load a single :soundfont and scan all its presets
        for sfont in self.soundfonts - {soundfont}:
            self.fluid.unload_soundfont(joinpath(self.sfdir, sfont))
        if {soundfont} - self.soundfonts:
            if not self.fluid.load_soundfont(joinpath(self.sfdir, soundfont)):
                self.soundfonts = set()
                self.sfpresets = [('No Presets'), 0, 0]
                return False
        self.soundfonts = {soundfont}

        self.sfpresets = []
        for bank in range(MAX_BANK):
            for preset in range(MAX_PRESET):
                name = self.fluid.get_preset_name(joinpath(self.sfdir, soundfont), bank, preset)
                if not name:
                    continue
                self.sfpresets.append((name, bank, preset))
        if not self.sfpresets:
            self.sfpresets = [('No Presets'), 0, 0]
            return False
        return True
        
    def select_sfpreset(self, presetnum):
        name, bank, prog = self.sfpresets[presetnum]
        if not self.soundfonts:
            return False
        soundfont = list(self.soundfonts)[0]
        if not self.fluid.program_select(0, joinpath(self.sfdir, soundfont), bank, prog):
            return False
        for channel in range(1, self.max_channels + 1):
            self.fluid.program_unset(channel)
        self.fluid.router_clear()
        self.fluid.router_default()
        return True
        
    def _midi_route(self, type, chan=None, par1=None, par2=None, **kwargs):
    # send midi message routing rules to fluidsynth (or perhaps mido in future)
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
        if isinstance(chan, FromToSpec):
            for chfrom in range(chan.from1, chan.from2 + 1):
                for chto in range(chan.to1, chan.to2 + 1):
                    chan_list = [chfrom - 1, chfrom - 1, 0, chto - 1]
                    self.fluid.router_addrule(type, chan_list, par1_list, par2_list)
        elif isinstance(chan, RouterSpec):
            for chfrom in range(chan.min, chan.max + 1):
                chan_list = [chfrom - 1, chfrom - 1, 0, chfrom * chan.mul + chan.add - 1]
                self.fluid.router_addrule(type, chan_list, par1_list, par2_list)
        else:
            self.fluid.router_addrule(type, None, par1_list, par2_list)

    def set_reverb(self, roomsize=None, damp=None, width=None, level=None):
        if 'fluidsettings' not in self.bank:
            self.bank['fluidsettings'] = {}
        if roomsize:
            self.bank['fluidsettings']['synth.reverb.room-size'] = roomsize
            self.fluid.setting('synth.reverb.room-size', roomsize)
        if damp:
            self.bank['fluidsettings']['synth.reverb.damp'] = damp
            self.fluid.setting('synth.reverb.room-size', damp)
        if width:
            self.bank['fluidsettings']['synth.reverb.width'] = width
            self.fluid.setting('synth.reverb.room-size', width)
        if level:
            self.bank['fluidsettings']['synth.reverb.level'] = level
            self.fluid.setting('synth.reverb.room-size', level)

    def get_reverb(self, roomsize=None, damp=None, width=None, level=None):
        params = ()
        if roomsize:
            params += self.fluid.get_setting('synth.reverb.room-size'),
        if damp:
            params += self.fluid.get_setting('synth.reverb.damp'),
        if width:
            params += self.fluid.get_setting('synth.reverb.width'),
        if level:
            params += self.fluid.get_setting('synth.reverb.level'),
        return params

    def set_chorus(self, nr=None, level=None, speed=None, depth=None):
        if 'fluidsettings' not in self.bank:
            self.bank['fluidsettings'] = {}
        if nr:
            self.bank['fluidsettings']['synth.chorus.nr'] = nr
            self.fluid.setting('synth.chorus.nr', nr)
        if level:
            self.bank['fluidsettings']['synth.chorus.level'] = level
            self.fluid.setting('synth.chorus.nr', level)
        if speed:
            self.bank['fluidsettings']['synth.chorus.speed'] = speed
            self.fluid.setting('synth.chorus.nr', speed)
        if depth:
            self.bank['fluidsettings']['synth.chorus.depth'] = depth
            self.fluid.setting('synth.chorus.nr', depth)

    def get_chorus(self, nr=None, level=None, speed=None, depth=None):
        params = ()
        if nr:
            params += self.fluid.get_setting('synth.chorus.nr'),
        if level:
            params += self.fluid.get_setting('synth.chorus.level'),
        if speed:
            params += self.fluid.get_setting('synth.chorus.speed'),
        if depth:
            params += self.fluid.get_setting('synth.chorus.depth'),
        return params

    def set_gain(self, gain):
        if 'fluidsettings' not in self.bank:
            self.bank['fluidsettings'] = {}
        self.bank['fluidsettings']['synth.gain'] = gain
        self.fluid.setting('synth.gain', gain)

    def get_gain(self):
        return self.fluid.get_setting('synth.gain')
