"""
Description: yaml extensions for fluidpatcher
"""
import re, oyaml

nn = '[A-G]?[b#]?\d+'
sfpex = re.compile('^(.+\.sf2):(\d+):(\d+)$', flags=re.I)
msgex = re.compile(f'^(note|cc|prog|pbend|cpress|kpress|noteoff):(\d+):({nn}):?(\d+)?$')
rspecex = re.compile(f'^({nn})-({nn})\*(-?[\d\.]+)([+-]{nn})$')
ftspecex = re.compile(f'^({nn})-?({nn})?=?(-?{nn})?-?(-?{nn})?$')

def sift(val):
    try:
        val = float(val)
    except (ValueError, TypeError):
        return val
    else:
        if val.is_integer():
            val = int(val)
        return val
        
def scinote_to_val(val):
    if not isinstance(val, str):
        return val
    sci = re.findall('([+-]?)([A-G])([b#]?)([0-9])', val)[0]
    sign = -1 if sci[0] == '-' else 1
    note = 'C D EF G A B'.find(sci[1])
    acc = ['b', '', '#'].index(sci[2]) - 1
    octave = int(sci[3])
    return sign * ((octave + 1) * 12 + note + acc)


class SFPreset(oyaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, sf, bank, prog):
        self.sf = sf
        self.bank = bank
        self.prog = prog
        
    def __repr__(self):
        return f"{self.sf}:{self.bank:03d}:{self.prog:03d}"

    @classmethod
    def from_yaml(cls, loader, node):
        sf, bank, prog = sfpex.findall(loader.construct_scalar(node))[0]
        bank = int(bank)
        prog = int(prog)
        return cls(sf, bank, prog)

#    @staticmethod
#    def to_yaml(dumper, data):
#        return dumper.represent_scalar('!sfpreset', str(data))


class RouterSpec(oyaml.YAMLObject):

    yaml_tag = '!rspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, min, max, mul, add, rep=None):
        self.min = scinote_to_val(min)
        self.max = scinote_to_val(max)
        self.mul = scinote_to_val(mul)
        self.add = scinote_to_val(add)
        if rep:
            self.rep = rep
        elif isinstance(add, (int, float)):
            self.rep = f"{min}-{max}*{mul}{add:+g}"
        else:
            self.rep = f"{min}-{max}*{mul}{add}"

    def __repr__(self):
        return self.rep

    @property
    def vals(self):
        return int(self.min), int(self.max), float(self.mul), int(self.add)
        
    @classmethod
    def from_yaml(cls, loader, node):
        spec = rspecex.search(loader.construct_scalar(node))
        min, max, mul, add = map(sift, spec.groups())
        return cls(min, max, mul, add, spec[0])
        
#    @staticmethod
#    def to_yaml(dumper, data):
#        return dumper.represent_scalar('!rspec', str(data))
        

class FromToSpec(RouterSpec):

    yaml_tag = '!ftspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, min, max, tomin, tomax, rep=None):
        self.min = scinote_to_val(min)
        self.max = scinote_to_val(max) if max != None else self.min
        self.tomin = scinote_to_val(tomin) if tomin != None else self.min
        if tomax != None: self.tomax = scinote_to_val(tomax)
        elif tomin != None: self.tomax = self.tomin
        else: self.tomax = self.max
        if self.min == self.max:
            self.mul = 1
        else:
            self.mul = (self.tomax - self.tomin) / (self.max - self.min)
        self.add = self.tomin - self.min * self.mul
        if rep: self.rep = rep
        else:
            self.rep = f"{min}"
            if max != '': self.rep += f"-{max}"
            if tomin != '': self.rep += f"={tomin}"
            if tomax != '': self.rep += f"-{tomax}"

    @classmethod
    def from_yaml(cls, loader, node):
        spec = ftspecex.search(loader.construct_scalar(node))
        min, max, tomin, tomax = map(sift, spec.groups())
        return cls(min, max, tomin, tomax, spec[0])
        
#    @staticmethod
#    def to_yaml(dumper, data):
#        return dumper.represent_scalar('!ftspec', str(data))
        

class MidiMsg(oyaml.YAMLObject):

    yaml_tag = '!midimsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, type, chan, par1, par2, rep=None):
        self.type = type
        self.chan = chan
        self.par1 = scinote_to_val(par1)
        self.par2 = par2
        if rep: self.rep = rep
        else:
            self.rep = f"{type}:{chan}:{par1}"
            if par2: self.rep += f":{par2}"

    def __repr__(self):
        return self.rep

    @classmethod
    def from_yaml(cls, loader, node):
        msg = msgex.search(loader.construct_scalar(node))
        type, chan, par1, par2 = map(sift, msg.groups())
        return cls(type, chan, par1, par2, msg[0])

#    @staticmethod
#    def to_yaml(dumper, data):
#        return dumper.represent_scalar('!ccmsg', str(data))


class MsgList(oyaml.YAMLObject):

    yaml_tag = '!msglist'
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
        
    @classmethod
    def from_yaml(cls, loader, node):
        return cls(loader.construct_sequence(node))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_sequence('!msglist', data, flow_style=True)


class RouterRule(oyaml.YAMLObject):

    yaml_tag = '!rrule'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, **kwargs):
        for a in kwargs:
            setattr(self, a, kwargs[a])

    def __iter__(self):
        return iter(self.__dict__.items())
        
    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!rrule', data, flow_style=True)


handlers = dict(Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

oyaml.add_implicit_resolver('!sfpreset', sfpex, **handlers)
oyaml.add_implicit_resolver('!midimsg', msgex, **handlers)
oyaml.add_implicit_resolver('!rspec', rspecex, **handlers)
oyaml.add_implicit_resolver('!ftspec', ftspecex, **handlers)

def resolve_path(tag, kind, *path):
    pathkeys = list(zip(path[::2], path[1::2]))
    oyaml.add_path_resolver(tag, pathkeys, kind=kind, **handlers)

snode = oyaml.SequenceNode
mnode = oyaml.MappingNode
resolve_path('!msglist', list, mnode, 'msg')
resolve_path('!msglist', list, mnode, 'init', mnode, 'msg')
resolve_path('!msglist', list, mnode, 'patches', mnode, None, mnode, 'msg')
resolve_path('!rrule', dict, mnode, 'router_rules', snode, None)
resolve_path('!rrule', dict, mnode, 'patches', mnode, None, mnode, 'router_rules', snode, None)
