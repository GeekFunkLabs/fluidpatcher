"""YAML extensions for fluidpatcher"""

from copy import deepcopy
import re

import yaml


TYPE_ALIAS = {}
for alts in [
    ['note', 'note_on', 'nt'],
    ['cc', 'control_change'],
    ['prog', 'program_change', 'pc'],
    ['pbend', 'pitchwheel', 'pb'],
    ['cpress', 'aftertouch', 'cp'],
    ['kpress', 'polytouch', 'kp'],
    ['sysex'],
    ['clock'],
    ['start'],
    ['continue'],
    ['stop']
]:
    for a in alts:
        TYPE_ALIAS[a] = alts[0]


class BankLoader(yaml.SafeLoader): pass


class BankDumper(yaml.SafeDumper): pass


class Bank:

    def __init__(self, text):
        data = yaml.load(text, Loader=BankLoader)
        names = data.get('names', {})
        def walk(node):
            if node is None:
                return None
            if hasattr(node, '_cure'):
                node._cure(names)
            if isinstance(node, (list, dict, _BankObject)):
                for item in node if isinstance(node, list) else node.values():
                    if walk(item) is None:
                        return None
            return node
        self.root = walk(data)
        self.patch = self.root.setdefault('patches', {})
        
    @property
    def patches(self):
        return list(self.patch)

    @property
    def soundfonts(self):
        """Set of all soundfonts used by patches"""
        sfonts = set()
        for zone in self:
            for item in zone.values():
                if isinstance(item, SFPreset):
                    sfonts.add(item.file)
        return sfonts

    def __getitem__(self, name):
        return _Patch(self.root, self.patch[name])

    def __setitem__(self, name, p):
        self.patch[name] = p

    def __delitem__(self, name):
        del self.patch[name]

    def __contains__(self, name):
        return name in self.patch

    def __len__(self):
        return len(self.patches)

    def __iter__(self):
        return iter([self.root, *self.patch.values()])

    def index(self, name):
        return list(self.patch).index(name)

    def dump(self):
        bank = self.root | {'patches': self.patch}
        return yaml.dump(bank, Dumper=BankDumper, sort_keys=False)


class _Patch:

    def __init__(self, root, patch):
        self._patch = patch
        self._root = root
        
    def __getitem__(self, name):    
        if isinstance(name, int):
            return self._patch.get(name) or self._root.get(name)
        elif name in ('rules', 'messages'):
            return self._root.get(name, []) + self._patch.get(name, [])
        else:
            return self._root.get(name, {}) | self._patch.get(name, {})

    def copy(self, **pars):
        return deepcopy(self._patch | pars)


class SFPreset(yaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile('^(.+\.sf2):(\d+):(\d+)$', flags=re.I)
    zone = None

    def __init__(self, file, bank, prog):
        self.file = file
        self.bank = int(bank)
        self.prog = int(prog)

    def __repr__(self):
        return f"{self.file}:{self.bank:03d}:{self.prog:03d}"

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(*loader.construct_scalar(node).split(':'))

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))


class _Parser:
    """metaclass for objects that can parse"""

    scinote = re.compile('([+-]?)([A-G])([b#]?)(-?[0-9])')

    def parse(self, s, names):
        """try to convert strings to numbers
           after performing name substitutions
           and/or scientific note name conversion
        """
        if s in names:
            s = names[s]
        if isinstance(s, str):
            if sci := self.scinote.match(s):
                sci = sci.groups('')
                sign = -1 if sci[0] == '-' else 1
                note = 'C D EF G A B'.find(sci[1])
                acc = ['b', '', '#'].index(sci[2]) - 1
                octave = int(sci[3])
                s = sign * ((octave + 1) * 12 + note + acc)
            else:
                try:
                    s = float(s)
                except (ValueError, TypeError):
                    pass
                else:
                    if s.is_integer():
                        s = int(s)
        return s


class MidiMessage(yaml.YAMLObject, _Parser):
    """Class for describing and storing MIDI messages
    """
    
    yaml_tag = '!midimsg'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(f'^({"|".join(TYPE_ALIAS)}):\S*$')
    zone = 'messages'
    zone_type = list

    def __init__(self, **pars):
        """Creates a MIDI message

        Args:
          type (required): MIDI message type
          chan: MIDI channel for voice messages
          num: note or controller number for note-on, note-off,
            control change, and key pressure message types
          val: value of the MIDI message, i.e. note velocity,
            controller value, pitch bend amount, pressure, or
            program number
        """
        self.__dict__.update(pars)
        if '_text' not in pars:
            match pars:
                case {'type': 'sysex', 'val': data}:
                    self._text = ':'.join(['sysex'] + [str(b) for b in data])
                case {'type': type, 'chan': chan, 'num': num, 'val': val}:
                    self._text = f"{type}:{chan}:{num}:{val}"
                case {'type': type, 'chan': chan, 'val': val}:
                    self._text = f"{type}:{chan}:{val}"
                case {'type': type}:
                    self._text = type
            self._cure()

    def __repr__(self):
        return self._text
        
    def copy(self, **pars):
        return MidiMessage(**self.__dict__ | pars)

    def _cure(self, names={}):
        self.type = TYPE_ALIAS[self.type]
        for par in 'chan', 'num', 'val':
            if hasattr(self, par):
                setattr(self, par, self.parse(getattr(self, par), names))

    @classmethod
    def from_yaml(cls, loader, node):
        text = loader.construct_scalar(node)
        match text.split(':'):
            case ['sysex', *data]:
                return cls(type='sysex', val=data)
            case [type, chan, num, val]:
                return cls(type=type, chan=chan, num=num, val=val, _text=text)
            case [type, chan, val]:
                return cls(type=type, chan=chan, val=val, _text=text)
            case [type]:
                return cls(type=type, _text=text)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))


class _BankObject(yaml.YAMLObject):
    """metaclass for mapping-type Bank data
    
    Attributes:
      opars: exact parameters as written in bank file, read-only
      pars: copy of opars with elements modified as needed
    """

    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    def __init__(self, **pars):
        self._pars = pars
        self.__dict__.update(pars)

    def __repr__(self):
        return str(self._pars)

    def __contains__(self, k):
        return k in self.__dict__

    def __iter__(self):
        return iter(self._pars.items())
        
    def values(self):
        return iter([v for k, v in self.__dict__.items() if k[0] != '_'])

    def copy(self, **pars):
        pars['_pars'] = self._pars | pars
        return self.__class__(**self.__dict__ | pars)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node, deep=True))
        
    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping(cls.yaml_tag, data, flow_style=cls.yaml_flow_style)


class _Route:

    def __init__(self, min, max, tomin, tomax, mul=None, add=None):
        self.min = min
        self.max = max
        self.tomin = tomin
        self.tomax = tomax
        if mul == None:
            self.mul = 1 if min == max else (tomax - tomin) / (max - min)
        else:
            self.mul = mul
        if add == None:
            self.add = tomin - min * self.mul
        else:
            self.add = add

    def __iter__(self):
        tovals = range(self.tomin, self.tomax + 1)
        return iter([_Route(self.min, self.max, n, n) for n in tovals])


class MidiRule(_BankObject, _Parser):
    """Class that describes responses to MIDI messages
    
    Attributes:
      type: MIDI message types to match
      totype: MIDI event type to produce
      chan, num, val: expressions describing the range of the
        corresponding message parameter to accept, and how to
        modify the parameter in the result.
      arbitrary additional parameters can be given as keyword arguments
    """
    ftroute = re.compile('^({0})?-?({0})?=?(-?{0})?-?(-?{0})?$'.format('[\w\d\#\.]+'))
    maroute = re.compile('^({0})-({0})\*(-?{0})([+-]{0})$'.format('[\w\d\#\.]+'))
    yaml_tag = '!midirule'
    yaml_flow_style = True
    zone = 'rules'
    zone_type = list

    def __init__(self, _cure=True, **pars):
        super().__init__(**pars)
        if _cure:
            self._cure()

    def __str__(self):
        return ', '.join([f"{k}: {v}" for k, v in self._pars.items()])

    def _cure(self, names={}):
        if not hasattr(self, 'totype'):
            types = self.type.split('=')
            self.type = TYPE_ALIAS[types[0]]
            self.totype = TYPE_ALIAS[types[-1]]
        for par in 'chan', 'num', 'val':
            spec = str(getattr(self, par, ''))
            if (m := self.ftroute.match(spec)) and any(m.groups()):
                min, max, tomin, tomax = [self.parse(x, names) for x in m.groups()]
                if min == None:
                    min, max = (1, 256) if par == 'chan' else (1, 127)
                elif max == None:
                    max = min
                if tomin == None:
                    tomin, tomax = min, max
                elif tomax == None:
                    tomax = tomin
                setattr(self, par, _Route(min, max, tomin, tomax))
            elif m := self.maroute.match(spec):
                min, max, mul, add = [self.parse(x, names) for x in m.groups()]
                tomin = min * mul + add
                tomax = max * mul + add
                setattr(self, par, _Route(min, max, tomin, tomax, mul, add))

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node) | dict(_cure=False))
        

class _MultiLineString(str, yaml.YAMLObject):

    yaml_tag = '!multilinestring'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style="|")


class _FlowList(list, yaml.YAMLObject):

    yaml_tag = '!flowlist'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile('.*?,')

    def __repr__(self):
        return self.text

    @classmethod
    def from_yaml(cls, loader, node):
        text = loader.construct_scalar(node)
        obj = cls([yaml.load(e, Loader=BankLoader) for e in text.split(',')])
        obj.text = text
        return obj

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))


class Sequence(_BankObject):

    yaml_tag = '!sequence'
    zone = 'sequences'
    zone_type = dict

    def __init__(self, **pars):
        super().__init__(**pars)
        if '\n' in pars['events']:
            self.events = []
            for p in pars['events'].strip().split('\n\n'):
                s = [[yaml.load(e, Loader=BankLoader) for e in r.split()]
                     for r in p.splitlines()]
                self.events.append([list(t) for t in zip(*s)])
            self._pars['events'] = _MultiLineString(self._pars['events'])
        if 'groove' in pars:
            if isinstance(pars['groove'], int):
                self.groove = [pars['groove'], 1]


class Arpeggio(_BankObject):

    yaml_tag = '!arpeggio'
    zone = 'arpeggios'
    zone_type = dict

    def __init__(self, **pars):
        super().__init__(**pars)
        self.style = pars['style']


class MidiLoop(_BankObject):

    yaml_tag = '!midiloop'
    zone = 'midiloops'
    zone_type = dict

    def __init__(self, **pars):
        super().__init__(**pars)
        self.beats = pars['beats']


class MidiFile(_BankObject):

    yaml_tag = '!midifile'
    zone = 'midifiles'
    zone_type = dict

    def __init__(self, **pars):
        super().__init__(**pars)
        self.file = pars['file']
        if 'jumps' in pars:
            self.jumps = [[int(t) for t in s.split('>')]
                          for s in pars['jumps']]


class LadspaEffect(_BankObject):

    yaml_tag = '!ladspafx'
    zone = 'ladspafx'
    zone_type = dict

    def __init__(self, **pars):
        super().__init__(**pars)
        self.lib = pars['lib']
        if 'chan' in pars:
            if not isinstance(pars['chan'], list):
                self.chan = [pars['chan']]
        if 'audio' in pars:
            if pars['audio'] == 'stereo':
                self.audio = 'Input L', 'Input R', 'Output L', 'Output R'
            elif pars['audio'] == 'mono':
                self.audio = 'Input', 'Output'


for cls in _BankObject.__subclasses__():
    path = ['patches', (dict, None), cls.zone, (cls.zone_type, None)]
    BankLoader.add_path_resolver(cls.yaml_tag, path, dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path, dict)
    BankLoader.add_path_resolver(cls.yaml_tag, path[-2:], dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path[-2:], dict)

for cls in (SFPreset, MidiMessage, _FlowList):
    BankLoader.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)
    BankDumper.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)

