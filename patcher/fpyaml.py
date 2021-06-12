"""
Description: yaml extensions for fluidpatcher
"""
import re, oyaml

sfpex = re.compile('^(.+):(\d+):(\d+)$')
ccmsgex = re.compile('^(\d+)/(\d+)=(\d+)$')
nn = '[A-G]?[b#]?\d+'
rspecex = re.compile(f'^({nn})-({nn})\*(-?[\d\.]+)([+-]{nn})$')
ftspecex = re.compile(f'^({nn})-?({nn})?=?(-?{nn})?-?(-?{nn})?$')

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


class SFPreset(oyaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, sf, bank, prog):
        self.sf = sf
        self.bank = bank
        self.prog = prog
        
    def __repr__(self):
        return '%s:%03d:%03d' % (self.sf, self.bank, self.prog)

    @classmethod
    def from_yaml(cls, loader, node):
        sf, bank, prog = sfpex.findall(loader.construct_scalar(node))[0]
        bank = int(bank)
        prog = int(prog)
        return cls(sf, bank, prog)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!sfpreset', str(data))


class RouterSpec(oyaml.YAMLObject):

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
    def from_yaml(cls, loader, node):
        route = rspecex.findall(loader.construct_scalar(node))[0]
        min, max, mul, add = map(sift, route)
        return cls(min, max, mul, add)
        
    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!rspec', str(data))
        

class FromToSpec(oyaml.YAMLObject):

    yaml_tag = '!ftspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, from1, from2, to1, to2):
        self._from1 = from1
        self._from2 = from2
        self._to1 = to1
        self._to2 = to2
        
    def __repr__(self):
        rep = f"{self.from1}"
        if self._from2 != '': rep += f"-{self._from2}"
        if self._to1 != '': rep += f"={self._to1}"
        if self._to2 != '': rep += f"-{self._to2}"
        return rep

    @property
    def from1(self):
        return scinote_to_val(self._from1)

    @property
    def from2(self):
        if self._from2 != '':
            return scinote_to_val(self._from2)
        return scinote_to_val(self._from1)

    @property
    def to1(self):
        if self._to1 != '':
            return scinote_to_val(self._to1)
        return self.from1
        
    @property
    def to2(self):
        if self._to2 != '':
            return scinote_to_val(self._to2)
        if self._to1 == '':
            return scinote_to_val(self._from2)
        return scinote_to_val(self._to1)
        
    @classmethod
    def from_yaml(cls, loader, node):
        spec = ftspecex.findall(loader.construct_scalar(node))[0]
        from1, from2, to1, to2 = map(sift, spec)
        return cls(from1, from2, to1, to2)
        
    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!ftspec', str(data))
        
    def routerspec(self):
        if self.from1 == self.from2:
            mul = 1
        else:
            mul = (self.to2 - self.to1) / (self.from2 - self.from1)
        add = self.to1 - self.from1 * mul
        return RouterSpec(self.from1, self.from2, mul, add)


class CCMsg(oyaml.YAMLObject):

    yaml_tag = '!ccmsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, chan, cc, val):
        self.chan = chan
        self.cc = cc
        self.val = val
        
    def __repr__(self):
        return '%d/%d=%d' % (self.chan, self.cc, self.val)

    @classmethod
    def from_yaml(cls, loader, node):
        msg = ccmsgex.findall(loader.construct_scalar(node))[0]
        chan, cc, val = map(int, msg)
        return cls(chan, cc, val)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!ccmsg', str(data))


class FlowSeq(oyaml.YAMLObject):

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
        
    @classmethod
    def from_yaml(cls, loader, node):
        return cls(loader.construct_sequence(node))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_sequence('!flowseq', data, flow_style=True)


class FlowMap(oyaml.YAMLObject):

    yaml_tag = '!flowmap'
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
        return dumper.represent_mapping('!flowmap', data, flow_style=True)


class RouterRule(FlowMap):
    
    yaml_tag = '!rrule'
    
class CCMsgList(FlowSeq):

    yaml_tag = '!cclist'


handlers = dict(Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

oyaml.add_implicit_resolver('!sfpreset', sfpex, **handlers)
oyaml.add_implicit_resolver('!ccmsg', ccmsgex, **handlers)
oyaml.add_implicit_resolver('!rspec', rspecex, **handlers)
oyaml.add_implicit_resolver('!ftspec', ftspecex, **handlers)

def resolve_path(tag, kind, *path):
    pathkeys = list(zip(path[::2], path[1::2]))
    oyaml.add_path_resolver(tag, pathkeys, kind=kind, **handlers)

snode = oyaml.SequenceNode
mnode = oyaml.MappingNode
resolve_path('!cclist', list, mnode, 'cc')
resolve_path('!cclist', list, mnode, 'init', mnode, 'cc')
resolve_path('!cclist', list, mnode, 'patches', mnode, None, mnode, 'cc')
resolve_path('!rrule', dict, mnode, 'router_rules', snode, None)
resolve_path('!rrule', dict, mnode, 'patches', mnode, None, mnode, 'router_rules', snode, None)
