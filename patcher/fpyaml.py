"""
Description: yaml extensions for fluidpatcher
"""
import re, oyaml

nn = '[A-G]?[b#]?\d*[.]?\d+' # parameter number or scientific note name 
sfp = re.compile('^(.+\.sf2):(\d+):(\d+)$', flags=re.I)
msg = re.compile(f'^(note|cc|prog|pbend|cpress|kpress|noteoff):(\d+):({nn}):?(\d+)?$')
syx = re.compile('^sysex:(.*?):(.+)$')
rte = re.compile(f'^({nn})-({nn})\*(-?[\d\.]+)([+-]{nn})$')
fts = re.compile(f'^({nn})?-?({nn})?=?(-?{nn})?-?(-?{nn})?$')
ft1 = re.compile(f'^({nn})-({nn})=?(-?{nn})?-?(-?{nn})?$')
ft2 = re.compile(f'^({nn})=(-?{nn})?-?(-?{nn})?$')
ft3 = re.compile(f'^=(-?{nn})-?(-?{nn})?$')

def sift(s):
    try:
        s = float(s)
    except (ValueError, TypeError):
        return s
    else:
        if s.is_integer():
            s = int(s)
        return s

def scinote_to_val(n):
    if not isinstance(n, str):
        return n
    sci = re.findall('([+-]?)([A-G])([b#]?)(-?[0-9])', n)[0]
    sign = -1 if sci[0] == '-' else 1
    note = 'C D EF G A B'.find(sci[1])
    acc = ['b', '', '#'].index(sci[2]) - 1
    octave = int(sci[3])
    return sign * ((octave + 1) * 12 + note + acc)

def totups(x):
    if isinstance(x, RouterSpec):
        return [(x.min, x.max, x.mul, x.add)]
    elif isinstance(x, list):
        return [(val, val, 1.0, 0) for val in x]
    elif isinstance(x, int):
        return [(x, x, 1.0, 0)]
    elif isinstance(x, str):
        return [(scinote_to_val(x), scinote_to_val(x), 1.0, 0)]
    else: return [None]

def tochantups(x):
    if isinstance(x, FromToSpec):
        return [(x.min - 1, x.max - 1, 0.0, chto)
                for chto in range(x.tomin - 1, x.tomax)]
    elif isinstance(x, RouterSpec):
        return [(x.min - 1, x.max - 1, x.mul, x.mul + x.add - 1)]
    elif isinstance(x, list):
        return [(ch - 1, ch - 1, 1.0, 0) for ch in x]
    elif isinstance(x, int):
        return [(x- 1, x - 1, 1.0, 0)]
    else: return [None]

def tochanset(x):
    if isinstance(x, RouterSpec):
        return set(range(x.min - 1, x.max))
    elif isinstance(x, list):
        return set([ch - 1 for ch in x])
    elif isinstance(x, int):
        return {x - 1}
    else: return set()

def iterdata(x):
    if isinstance(x, (list, dict)):
        for item in x if isinstance(x, list) else x.values():
            if item is None: return None
            elif isinstance(item, (list, dict)):
                if iterdata(item) is None: return None
    return x

def parse(text):
    return iterdata(oyaml.safe_load(text))

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


class MidiMsg(oyaml.YAMLObject):

    yaml_tag = '!midimsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, type, chan, par1, par2=None, yaml=''):
        self.type = type
        self.chan = chan - 1
        self.par1 = scinote_to_val(par1)
        self.par2 = par2
        self.argstr = ', '.join(map(str, [type, chan, par1, par2]))
        self.yaml = yaml

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


class SysexMsg(MidiMsg):

    yaml_tag = '!syxmsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, dest, data=[], file='', yaml=''):
        self.dest = dest
        self.data = data
        self.file = file
        self.argstr = ', '.join(map(str, [dest, data, file, yaml]))
        self.yaml = yaml

    def __iter__(self):
        return iter(self.data)

    @classmethod
    def from_yaml(cls, loader, node):
        s = syx.search(loader.construct_scalar(node))
        if ':' in  s[2]:
            try:
                data = list(map(int, s[2].split(':')))
            except ValueError:
                data = list(map(lambda x: int(x, 16), s[2].split(':')))
            finally: return cls(s[1], data=[data], yaml=s[0])
        else: return cls(s[1], file=s[2], yaml=s[0])

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!syxmsg', str(data))


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
        if min == None: min, max = 0, 127
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
        if 'type2' in apars: # convert older style
            type = f"{type.split('=')[0]}={apars.pop('type2')}"
        self.type = type.split('=')
        self.chan = tochantups(chan)
        self.par1 = totups(par1)
        self.par2 = totups(par2)[0]
        self.apars = apars
        rule = dict(type=type)
        if chan: rule['chan'] = chan
        if par1: rule['par1'] = par1
        if par2: rule['par2'] = par2
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


handlers = dict(Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_implicit_resolver('!sfpreset', sfp, **handlers)
oyaml.add_implicit_resolver('!midimsg', msg, **handlers)
oyaml.add_implicit_resolver('!syxmsg', syx, **handlers)
oyaml.add_implicit_resolver('!rspec', rte, **handlers)
oyaml.add_implicit_resolver('!ftspec', ft1, **handlers)
oyaml.add_implicit_resolver('!ftspec', ft2, **handlers)
oyaml.add_implicit_resolver('!ftspec', ft3, **handlers)
seqnode = oyaml.SequenceNode
mapnode = oyaml.MappingNode
oyaml.add_path_resolver('!rrule', [(mapnode, 'router_rules'), (seqnode, None)], dict, **handlers)
oyaml.add_path_resolver('!rrule', [(mapnode, 'patches'), (mapnode, None), (mapnode, 'router_rules'), (seqnode, None)], dict, **handlers)
