"""
Copyright (c) 2020 Bill Peterson

Description: extensions to YAML classes for patcher
"""
import re, oyaml
from oyaml import safe_load, safe_load_all, safe_dump, safe_dump_all, YAMLError, YAMLObject
from oyaml import SequenceNode as snode, MappingNode as mnode


def sift(val):
    try:
        val = float(val)
    except ValueError:
        return val
    else:
        if val.is_integer():
            val = int(val)
        return val
        
def scinote_to_val(val):
    if not isinstance(val, str):
        return val
    sci = re.findall('([+-]?)([A-G])([b#]?)([0-9])', val)[0]
    sign = ('+ -'.find(sci[0]) - 1) * -1
    note = 'C_D_EF_G_A_B'.find(sci[1])
    acc = (' #b'.find(sci[2]) + 1) % 3 - 1
    octave = int(sci[3])
    return sign * ((octave + 1) * 12 + note + acc)


handlers = dict(Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

sfpex = re.compile('^(.+):(\d+):(\d+)$')
oyaml.add_implicit_resolver('!sfpreset', sfpex, **handlers)

class SFPreset(YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, name, bank, prog):
        self.name = name
        self.bank = bank
        self.prog = prog
        
    def __repr__(self):
        return '%s:%03d:%03d' % (self.name, self.bank, self.prog)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!sfpreset', str(data))

    @classmethod
    def from_yaml(cls, loader, node):
        name, bank, prog = sfpex.findall(loader.construct_scalar(node))[0]
        bank = int(bank)
        prog = int(prog)
        return cls(name, bank, prog)


ccmsgex = re.compile('^([0-9]+)/([0-9]+)=([0-9]+)$')
oyaml.add_implicit_resolver('!ccmsg', ccmsgex, **handlers)

class CCMsg(YAMLObject):

    yaml_tag = '!ccmsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, chan, cc, val):
        self.chan = chan
        self.cc = cc
        self.val = val
        
    def __repr__(self):
        return '%d/%d=%d' % (self.chan, self.cc, self.val)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!ccmsg', str(data))

    @classmethod
    def from_yaml(cls, loader, node):
        msg = ccmsgex.findall(loader.construct_scalar(node))[0]
        chan, cc, val = map(int, msg)
        return cls(chan, cc, val)


rspecex = re.compile('^([\d\.A-Gb#]+)-([\d\.A-Gb#]+)\*(-?[\d\.]+)([+-][\d\.A-Gb#]+)$')
oyaml.add_implicit_resolver('!rspec', rspecex, **handlers)

class RouterSpec(YAMLObject):

    yaml_tag = '!rspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add

    def __repr__(self):
        if isinstance(self.add, int):
            return '%s-%s*%s%+d' % (self.min, self.max, self.mul, self.add)
        elif isinstance(self.add, float):
            return '%s-%s*%s%+f' % (self.min, self.max, self.mul, self.add)
        else:
            return '%s-%s*%s%s' % (self.min, self.max, self.mul, self.add)
        
    @property
    def vals(self):
        v = list(map(scinote_to_val, [self.min, self.max, self.mul, self.add]))
        return int(v[0]), int(v[1]), float(v[2]), int(v[3])
        
    @classmethod
    def fromtospec(cls, spec):
        from1, from2, to1, to2 = spec.vals
        mul = (to2 - to1) / (from2 - from1)
        add = to1 - from1 * mul
        return cls(from1, from2, mul, add)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!rspec', str(data))
        
    @classmethod
    def from_yaml(cls, loader, node):
        route = rspecex.findall(loader.construct_scalar(node))[0]
        min, max, mul, add = map(sift, route)
        return cls(min, max, mul, add)
        
        
ftspecex = re.compile('^([\d\.A-Gb#]+)-([\d\.A-Gb#]+)=(-?[\d\.A-Gb#]+)-(-?[\d\.A-Gb#]+)$')
oyaml.add_implicit_resolver('!ftspec', ftspecex, **handlers)

class FromToSpec(YAMLObject):

    yaml_tag = '!ftspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, from1, from2, to1, to2):
        self.from1 = from1
        self.from2 = from2
        self.to1 = to1
        self.to2 = to2
        
    def __repr__(self):
        return '%s-%s=%s-%s' % (data.from1, data.from2, data.to1, data.to2)
        
    @property
    def vals(self):
        v = list(map(scinote_to_val, [self.from1, self.from2, self.to1, self.to2]))
        return int(v[0]), int(v[1]), float(v[2]), int(v[3])
        
    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!ftspec', str(data))

    @classmethod
    def from_yaml(cls, loader, node):
        spec = ftspecex.findall(loader.construct_scalar(node))[0]
        from1, from2, to1, to2 = map(sift, spec)
        return cls(from1, from2, to1, to2)
        

class FlowSeq(YAMLObject):

    yaml_tag = '!flowseq'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)
        
    def __add__(self, addend):
        if isinstance(addend, FlowSeq):
            return FlowSeq(self.items + addend.items)
        else:
            return self.items + addend
        
    def __radd__(self, addend):
        return addend + self.items
        
    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_sequence('!flowseq', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(loader.construct_sequence(node))


class FlowMap(YAMLObject):

    yaml_tag = '!flowmap'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, **kwargs):
        for a in kwargs:
            setattr(self, a, kwargs[a])

    def __iter__(self):
        return iter(self.__dict__.items())

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!flowmap', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node))


def resolve_as_flowmap(*path):
    pathkeys = zip(path[::2], path[1::2])
    oyaml.add_path_resolver('!flowmap', pathkeys, kind=dict, **handlers)
    
def resolve_as_flowseq(*path):
    pathkeys = zip(path[::2], path[1::2])
    oyaml.add_path_resolver('!flowseq', pathkeys, kind=list, **handlers)

resolve_as_flowseq(mnode, 'cc')
resolve_as_flowseq(mnode, 'init', mnode, 'cc')
resolve_as_flowseq(mnode, 'patches', mnode, None, mnode, 'cc')

resolve_as_flowmap(mnode, 'router_rules', snode, None) 
resolve_as_flowmap(mnode, 'patches', mnode, None, mnode, 'router_rules', snode, None) 

resolve_as_flowmap(mnode, 'cclinks', snode, None)
resolve_as_flowmap(mnode, 'patches', mnode, None, mnode, 'cclinks', snode, None)

resolve_as_flowmap(mnode, 'effects', snode, None, mnode, 'controls', snode, None)
resolve_as_flowmap(mnode, 'patches', mnode, None, mnode, 'effects', snode, None, mnode, 'controls', snode, None)
