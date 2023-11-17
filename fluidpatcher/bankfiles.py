"""YAML extensions for fluidpatcher
"""

import re
import yaml

sfp = re.compile('^(.+\.sf2):(\d+):(\d+)$', flags=re.I)
nn = '[A-G]?[b#]?\d*[.]?\d+' # scientific note name or number
msg = re.compile(f'^(note|cc|prog|pbend|cpress|kpress|noteoff):(\d+):({nn}):?(\d+)?$')
rspec = re.compile(f'^({nn})-({nn})\*(-?[\d\.]+)([+-]{nn})$')
ftspec = re.compile(f'^({nn})?-?({nn})?=?(-?{nn})?-?(-?{nn})?$')
scinote = re.compile('([+-]?)([A-G])([b#]?)(-?[0-9])') # scientific note name parts

handlers = dict(Loader=yaml.SafeLoader, Dumper=yaml.SafeDumper)
yaml.add_implicit_resolver('!sfpreset', sfp, **handlers)
yaml.add_implicit_resolver('!midimsg', msg, **handlers)

def add_bankobj_resolver(tag, path, kind):
    yaml.add_path_resolver(tag, path, kind, **handlers)
    yaml.add_path_resolver(tag, ['patches', (dict, None), *path], kind, **handlers)

add_bankobj_resolver('!rrule', ['router_rules', (list, None)], dict)
add_bankobj_resolver('!midiplayer', ['midiplayers', (dict, None)], dict)
add_bankobj_resolver('!sequencer', ['sequencers', (dict, None)], dict)
add_bankobj_resolver('!arpeggiator', ['arpeggiators', (dict, None)], dict)
add_bankobj_resolver('!ladspafx', ['ladspafx', (dict, None)], dict)

def scinote_to_val(n):
    """convert scientific note name to MIDI note number
    """
    if not isinstance(n, str):
        return n
    sci = scinote.findall(n)[0]
    sign = -1 if sci[0] == '-' else 1
    note = 'C D EF G A B'.find(sci[1])
    acc = ['b', '', '#'].index(sci[2]) - 1
    octave = int(sci[3])
    return sign * ((octave + 1) * 12 + note + acc)

def sift(s):
    """attempt to convert strings into floats or ints
    """
    try: s = float(s)
    except (ValueError, TypeError): return s
    return int(s) if s.is_integer() else s

def parseyaml(text='', data={}):
    """prune branches that contain None instances"""
    data = yaml.safe_load(text) if text else data
    if isinstance(data, (list, dict)):
        for item in data if isinstance(data, list) else data.values():
            if item is None: return None
            elif isinstance(item, (list, dict)):
                if parseyaml(data=item) is None: return None
    return data

def renderyaml(data):
    """sort_keys=False preserves dict order"""
    return yaml.safe_dump(data, sort_keys=False)


class SFPreset(yaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper

    def __init__(self, sfont, bank, prog):
        self.sfont = sfont
        self.bank = bank
        self.prog = prog
        
    def __str__(self):
        return f"{self.sfont}:{self.bank:03d}:{self.prog:03d}"

    @classmethod
    def from_yaml(cls, loader, node):
        sfont, bank, prog = sfp.search(loader.construct_scalar(node)).groups()
        bank = int(bank)
        prog = int(prog)
        return cls(sfont, bank, prog)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!sfpreset', str(data))


class MidiMessage(yaml.YAMLObject):

    yaml_tag = '!midimsg'
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper

    def __init__(self, type, chan, par1, par2=None, yaml=''):
        self.type = type
        self.chan = chan
        self.par1 = scinote_to_val(par1)
        self.par2 = par2
        self.yaml = yaml or f"{type}:{chan}:{par1}:{par2}"

    def __str__(self):
        return self.yaml

    def __iter__(self):
        return iter([self.type, self.chan, self.par1, self.par2])

    @classmethod
    def from_yaml(cls, loader, node):
        m = msg.search(loader.construct_scalar(node))
        type, chan, par1, par2 = [sift(g) for g in m.groups()]
        return cls(type, chan, par1, par2, m[0])

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!midimsg', str(data))


class BankObject(yaml.YAMLObject):
    """Translation layer between YAML representation and bank data
    
    Attributes:
      opars: exact parameters as written in bank file, read-only
      pars: copy of opars with elements modified as needed
    """

    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper

    def __init__(self, **pars):
        self.opars = {**pars}
        self.pars = {**pars}

    def __str__(self):
        return str(self.opars)

    def __iter__(self):
        return iter(self.opars.items())

    def __setitem__(self, key, val):
        self.pars[key] = val

    def __getitem__(self, key):
        return self.pars[key]

    def keys(self):
        return self.pars.keys()

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node))


class RouterRule(BankObject):

    yaml_tag = '!rrule'

    def __init__(self, **pars):
        super().__init__(**pars)
        try:
            type = self.pars.pop('type').split('=')[:2]
        except KeyError as e:
            raise AttributeError("Router rule must have a type.") from e
        if 'type2' in pars: type.append(self.pars.pop('type2')) # old format
        self.type = [(t, type[-1]) for t in type[0].split('|')]
        self.chan = ChannelSpec(self.pars.pop('chan', ''))
        self.pars['par1'] = ParamSpec(pars.get('par1', ''))
        self.pars['par2'] = ParamSpec(pars.get('par2', ''))

    def add(self, addfunc):
        for type in self.type:
            for chan in self.chan:
                addfunc(type, chan, **self.pars)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!rrule', data, flow_style=True)


class Arpeggiator(BankObject):

    yaml_tag = '!arpeggiator'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'groove' in pars:
            if isinstance(pars['groove'], int):
                self.pars['groove'] = [pars['groove'], 1]
            elif isinstance(pars['groove'], str):
                self.pars['groove'] = [int(a) for a in pars['groove'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!arpeggiator', data)


class Sequencer(Arpeggiator):

    yaml_tag = '!sequencer'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'notes' in pars:
            if isinstance(pars['notes'], str):
                self.pars['notes'] = [MidiMessage.from_yaml(yaml.SafeLoader, n.strip())
                                      for n in pars['notes'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!sequencer', data)


class MidiPlayer(BankObject):

    yaml_tag = '!midiplayer'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'chan' in pars:
            self.pars['chan'] = ChannelSpec(pars['chan']).tups[0]
        if 'mask' in pars:
            if isinstance(pars['mask'], str):
                self.pars['mask'] = [t.strip() for t in pars['mask'].split(',')]
        if 'loops' in pars:
            if isinstance(pars['loops'], str):
                self.pars['loops'] = [int(t) for t in pars['loops'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!midiplayer', data)


class LadspaEffect(BankObject):

    yaml_tag = '!ladspafx'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'group' in pars:
            if isinstance(pars['group'], int):
                self.pars['group'] = [pars['group']]
            elif isinstance(pars['group'], str):
                self.pars['group'] = [int(t) for t in pars['group'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!ladspafx', data)


class ParamSpec:
    
    def __init__(self, text):
        self.text = str(text)
        if not text:
            self.tups = []
        elif spec := rspec.match(self.text):
            min, max, mul, add = [scinote_to_val(sift(x)) for x in spec.groups()]
            self.tups = min, max, mul, add
        elif spec := ftspec.match(self.text):
            min, max, tomin, tomax = [scinote_to_val(sift(x)) for x in spec.groups()]
            if min == None: min, max = 0, 127
            if max == None: max = min
            if tomin == None and tomax == None: tomin, tomax = min, max
            elif tomax == None: tomax = tomin
            mul = 1 if min == max else (tomax - tomin) / (max - min)
            add = tomin - min * mul
            self.tups = min, max, mul, add
        else:
            self.tups = []
            
    def __iter__(self):
        return iter(self.tups)

    def __str__(self):
        return self.text

    def __bool__(self):
        return bool(self.tups)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(loader.construct_scalar(node))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!chspec', str(data))


class ChannelSpec(ParamSpec):
    
    def __init__(self, text):
        self.text = str(text)
        if not text:
            self.tups = []
        elif spec := rspec.match(self.text):
            min, max, mul, add = [sift(x) for x in spec.groups()]
            self.tups = [(min, max, mul, add)]
        elif spec := ftspec.match(self.text):
            min, max, tomin, tomax = [sift(x) for x in spec.groups()]
            if min == None: min, max = 1, 256
            if max == None: max = min
            if tomin == None: tomin = min
            if tomax == None: tomax = max if tomin == None else tomin
            mul = 1 if min == max else (tomax - tomin) / (max - min)
            add = tomin - min * mul
            self.tups = [(min, max, 0.0, chto)
                         for chto in range(tomin, tomax + 1)]
        else:
            self.tups = []
