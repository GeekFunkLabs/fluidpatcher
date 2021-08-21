"""
Description: yaml extensions for fluidpatcher
"""
import re, oyaml

nn = '[A-G]?[b#]?\d+'
sfp = re.compile('^(.+\.sf2):(\d+):(\d+)$', flags=re.I)
rte = re.compile(f'^({nn})-({nn})\*(-?[\d\.]+)([+-]{nn})$')
fts = re.compile(f'^({nn})-?({nn})?=?(-?{nn})?-?(-?{nn})?$')
ft1 = re.compile(f'^({nn})-({nn})=?(-?{nn})?-?(-?{nn})?$')
ft2 = re.compile(f'^({nn})=(-?{nn})?-?(-?{nn})?$')
msg = re.compile(f'^(note|cc|prog|pbend|cpress|kpress|noteoff):(\d+):({nn}):?(\d+)?$')

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

def totups(obj):
    if isinstance(obj, RouterSpec):
        return [(obj.min, obj.max, obj.mul, obj.add)]
    elif isinstance(obj, list):
        return [(val, val, 1.0, 0) for val in obj]
    elif isinstance(obj, int):
        return [(obj, obj, 1.0, 0)]
    else: return [None]

def tochantups(obj):
    if isinstance(obj, FromToSpec):
        return [(obj.min - 1, obj.max - 1, 0.0, chto)
                for chto in range(obj.tomin - 1, obj.tomax)]
    elif isinstance(obj, RouterSpec):
        return [(obj.min - 1, obj.max - 1, obj.mul, obj.mul + obj.add - 1)]
    elif isinstance(obj, list):
        return [(ch - 1, ch - 1, 1.0, 0) for ch in obj]
    elif isinstance(obj, int):
        return [(obj- 1, obj - 1, 1.0, 0)]
    else: return [None]
    
def tochanset(obj):
    if isinstance(obj, RouterSpec):
        return set(range(obj.min - 1, obj.max))
    elif isinstance(obj, list):
        return set([ch - 1 for ch in obj])
    elif isinstance(obj, int):
        return {obj - 1}
    else: return set()
    
def parse(text):
    return oyaml.safe_load(text)

def render(data):
    return oyaml.safe_dump(data)


class SFPreset(oyaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, sf, bank, prog):
        self.sf = sf
        self.bank = bank
        self.prog = prog
        
    def __repr__(self):
        return f"{self.__class__.__name__}({self.sf}, {self.bank}, {self.prog})"

    def __str__(self):
        return f"{self.sf}:{self.bank:03d}:{self.prog:03d}"

    @classmethod
    def from_yaml(cls, loader, node):
        sf, bank, prog = sfp.search(loader.construct_scalar(node)).groups()
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
    
    def __init__(self, min, max, mul, add, yaml=''):
        self.min = scinote_to_val(min)
        self.max = scinote_to_val(max)
        self.mul = scinote_to_val(mul)
        self.add = scinote_to_val(add)
        self.argstr = ', '.join(map(str, [min, max, mul, add]))
        self.yaml = yaml

    def __repr__(self):
        return f"{self.__class__.__name__}({self.argstr})"

    def __str__(self):
        return self.yaml

    @classmethod
    def from_yaml(cls, loader, node):
        spec = rte.search(loader.construct_scalar(node))
        min, max, mul, add = map(sift, spec.groups())
        return cls(min, max, mul, add, spec[0])

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!rspec', str(data))


class FromToSpec(RouterSpec):

    yaml_tag = '!ftspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, min, max, tomin, tomax, yaml=''):
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
        self.argstr = ', '.join(map(str, [min, max, tomin, tomax]))
        self.yaml = yaml

    @classmethod
    def from_yaml(cls, loader, node):
        spec = fts.search(loader.construct_scalar(node))
        min, max, tomin, tomax = map(sift, spec.groups())
        return cls(min, max, tomin, tomax, spec[0])
        
    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!ftspec', str(data))


class RouterRule(oyaml.YAMLObject):

    yaml_tag = '!rrule'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, type='', chan=None, par1=None, par2=None, **apars):
        self.type = type
        self.chan = tochantups(chan)
        self.par1 = totups(par1)
        self.par2 = totups(par2)[0]
        self.apars = apars
        rule = {'type': type}
        for par, val in [('chan', chan), ('par1', par1), ('par2', par2)]:
            if val != None: rule[par] = val
        self.rule = {**rule, **apars}
        self.kwstr = ', '.join([f"{k}={v}" for k, v in self.rule.items()])

    def __repr__(self):
        return f"{self.__class__.__name__}({self.kwstr})"

    def __str__(self):
        return str(self.rule)

    def __iter__(self):
        return iter(self.rule.items())

    def add(self, addfunc):
        for chan in self.chan:
            for par1 in self.par1:
                addfunc(self.type, chan, par1, self.par2, **self.apars)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!rrule', data, flow_style=True)


class MidiMsg(oyaml.YAMLObject):

    yaml_tag = '!midimsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, type, chan, par1, par2, yaml=''):
        self.type = type
        self.chan = chan - 1
        self.par1 = scinote_to_val(par1)
        self.par2 = par2
        self.argstr = ', '.join(map(str, [type, chan, par1, par2]))
        self.yaml = yaml
#        if rep: self.rep = rep
#        else:
#            self.rep = f"{type}:{chan}:{par1}"
#            if par2 != '': self.rep += f":{par2}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.argstr})"

    def __str__(self):
        return self.yaml

    def __iter__(self):
        return iter([self.type, self.chan, self.par1, self.par2])

    @classmethod
    def from_yaml(cls, loader, node):
        m = msg.search(loader.construct_scalar(node))
        type, chan, par1, par2 = map(sift, m.groups())
        return cls(type, chan, par1, par2, m[0])

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!midimsg', str(data))


handlers = dict(Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_implicit_resolver('!sfpreset', sfp, **handlers)
oyaml.add_implicit_resolver('!rspec', rte, **handlers)
oyaml.add_implicit_resolver('!ftspec', ft1, **handlers)
oyaml.add_implicit_resolver('!ftspec', ft2, **handlers)
oyaml.add_implicit_resolver('!midimsg', msg, **handlers)
seqnode = oyaml.SequenceNode
mapnode = oyaml.MappingNode
oyaml.add_path_resolver('!rrule', [(mapnode, 'router_rules'), (seqnode, None)], dict, **handlers)
oyaml.add_path_resolver('!rrule', [(mapnode, 'patches'), (mapnode, None), (mapnode, 'router_rules'), (seqnode, None)], dict, **handlers)
