"""YAML extensions for fluidpatcher"""

import re
import yaml


class BankLoader(yaml.SafeLoader): pass

class BankDumper(yaml.SafeDumper): pass


class Bank:

    def __init__(self, text):
        data = Bank.loadyaml(text)
        self.patches = data.get('patches', {})
        self.root = data
        names = self.root.get('names', {})
        for zone in self:
            for rule in zone.get('rules', []):
                rule._cure(names)
            for msg in zone.get('messages', []):
                msg._cure(names)
            for seq in zone.get('sequencers', {}).values():
                for msg in seq.notes:
                    msg._cure(names)
        for msg in self.root.get('init', {}).get('messages', []):
            msg._cure(names)
        
    def __getitem__(self, name):
        if name in self.patches:
            patch = self.patches[name]
        elif isinstance(name, int):
            patch = list(self.patches.values())[name % len(self.patches)]
        return Patch(self.root, patch)

    def __len__(self):
        return len(self.patches)

    def __iter__(self):
        return iter([self.root, *self.patches.values()])

    @property
    def soundfonts(self):
        """Set of all soundfonts used by patches"""
        sfonts = set()
        for zone in self:
            for item in zone:
                if isinstance(item, int):
                    sfonts.add(zone[item].file)
        return sfonts

    def dump(self):
        bank = self.root | ({'patches': self.patches} if self.patches else {})
        return Bank.dumpyaml(bank)

    @staticmethod
    def loadyaml(text='', data={}):
        if text:
            data = yaml.load(text, Loader=BankLoader)
        """prune branches that contain None instances"""
        if isinstance(data, (list, dict)):
            for item in data.values() if isinstance(data, dict) else data:
                if item is None:
                    return None
                elif isinstance(item, (list, dict)):
                    if Bank.loadyaml(data=item) is None:
                        return None
        return data

    @staticmethod
    def dumpyaml(data):
        """sort_keys=False preserves dict order"""
        return yaml.dump(data, Dumper=BankDumper, sort_keys=False)


class Patch:

    def __init__(self, root, patch):
        self.patch = patch
        self.root = root
        
    def __getitem__(self, name):
        if isinstance(name, int):
            return self.patch.get(name) or self.root.get(name)
        elif name in ('rules', 'messages'):
            return self.root.get(name, []) + self.patch.get(name, [])
        else:
            return self.root.get(name, {}) | self.patch.get(name, {})


class SFPreset(yaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    def __init__(self, file, bank, prog):
        self.file = file
        self.bank = int(bank)
        self.prog = int(prog)

    def __repr__(self):
        return f"{self.file}:{self.bank:03d}:{self.prog:03d}"

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(*loader.construct_scalar(node).split(':'))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!sfpreset', str(data))


class _Parser:
    """metaclass for objects that can parse"""

    scinote = re.compile('([+-]?)([A-G])([b#]?)(-?[0-9])')

    @staticmethod
    def parse(s, names={}):
        """try to convert strings to numbers
           after performing name substitutions
           and/or scientific note name conversion
        """
        if s in names:
            s = names[s]
        if isinstance(s, str):
            if sci := _Parser.scinote.match(s):
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
                    s = int(s) if s.is_integer else s
        return s


class MidiMessage(yaml.YAMLObject, _Parser):

    yaml_tag = '!midimsg'
    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    def __init__(self, type='', chan=1, num=0, val=0, text='', cure=True):
        self._text = text
        self.type = type
        self.chan = chan
        self.num = num
        self.val = val
        if b := text.split(':'):
            if b[0] == 'sysex':
                self.type, self.val = b[0], b[1:]
            elif len(b) == 3:
                self.type, self.chan, self.val = b[:]
            elif len(b) == 4:
                self.type, self.chan, self.num, self.val = b[:]
            else:
                self.type = b[0]                
        else:
            if self.type == 'sysex':
                data = [int(b) for b in self.val]
                self._text = f"sysex:{':'.join(data)}"
            else:
                parts = [p for p in (type, chan, num, val) if p != None]
                self._text = ':'.join(parts)
        if cure:
            self._cure()

    def __repr__(self):
        return self._text

    def _cure(self, names={}):
        for b in 'chan', 'num', 'val':
            setattr(self, b, self.parse(getattr(self, b), names))

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(text=loader.construct_scalar(node), cure=False)

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_scalar('!midimsg', str(data))


class _BankObject(yaml.YAMLObject):
    """metaclass for mapping-type Bank data
    
    Attributes:
      opars: exact parameters as written in bank file, read-only
      pars: copy of opars with elements modified as needed
    """

    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    def __init__(self, **pars):
        self._opars = pars
        self.__dict__.update(pars)

    def __contains__(self, k):
        return k in self.__dict__

    def __iter__(self):
        return iter(self._opars.items())

    @property
    def pars(self):
        return {k: v for k, v in self.__dict__.items() if k != '_opars'}

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node))


class RouterRule(_BankObject, _Parser):

    yaml_tag = '!rrule'
    fluidspec = re.compile('^({0})-({0})\*(-?{0})([+-]{0})$'.format('[\w\d\#\.]+'))
    fromtospec = re.compile('^({0})?-?({0})?=?(-?{0})?-?(-?{0})?$'.format('[\w\d\#\.]+'))

    def __init__(self, cure=True, **pars):
        super().__init__(**pars)
        types = self.type.split('=')
        self.type = types[0], types[-1]
        if cure:
            self._cure()

    def __repr__(self):
        return str(self._opars)

    def _add(self, addfunc):
        for chan in self.chan or [None]:
            addfunc(**self.pars | {'chan': chan})

    def _cure(self, names={}):
        chan = str(getattr(self, 'chan', ''))
        num = str(getattr(self, 'num', ''))
        val = str(getattr(self, 'val', ''))
        self.chan = self.chantuples(chan, names)
        self.num = self.partuple(num, names)
        self.val = self.partuple(val, names)

    def chantuples(self, text, names):
        spec = []
        if args := self.fluidspec.match(text):
            min, max, mul, add = [self.parse(x, names) for x in args.groups()]
            for fromchan in range(min, max + 1):
                spec += [(fromchan, fromchan * mul + add)]
        elif any(args := self.fromtospec.match(text).groups()):
            min, max, tomin, tomax = [self.parse(x, names) for x in args]
            if min == None:
                min, max = 1, 256
            if max == None:
                max = min
            if tomin == None:
                tomin = min
            if tomax == None:
                tomax = max if tomin == None else tomin
            for fromchan in range(min, max + 1):
                for tochan in range(tomin, tomax + 1):
                    spec += [(fromchan, tochan)]
        return spec

    def partuple(self, text, names):
        if args := self.fluidspec.match(text):
            min, max, mul, add = [self.parse(x, names) for x in args.groups()]
            return min, max, mul, add
        elif any(args := self.fromtospec.match(text).groups()):
            min, max, tomin, tomax = [self.parse(x, names) for x in args]
            if min == None:
                min, max = 0, 127
            if max == None:
                max = min
            if tomin == None and tomax == None:
                tomin, tomax = min, max
            elif tomax == None:
                tomax = tomin
            mul = 1 if min == max else (tomax - tomin) / (max - min)
            add = tomin - min * mul
            return min, max, mul, add
        else:
            return ()

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(**loader.construct_mapping(node) | dict(cure=False))

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!rrule', data, flow_style=True)
        

class Arpeggiator(_BankObject):

    yaml_tag = '!arpeggiator'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'groove' in pars:
            if isinstance(pars['groove'], int):
                self.groove = [pars['groove'], 1]
            elif isinstance(pars['groove'], str):
                self.groove = [int(a) for a in pars['groove'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!arpeggiator', data)


class Sequencer(_BankObject):

    yaml_tag = '!sequencer'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'groove' in pars:
            if isinstance(pars['groove'], int):
                self.groove = [pars['groove'], 1]
            elif isinstance(pars['groove'], str):
                self.groove = [int(a) for a in pars['groove'].split(',')]
        if 'notes' in pars:
            if isinstance(pars['notes'], str):
                self.groove = [MidiMessage(n) for n in pars['notes'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!sequencer', data)


class MidiPlayer(_BankObject):

    yaml_tag = '!midiplayer'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'mask' in pars:
            if isinstance(pars['mask'], str):
                self.mask = [t.strip() for t in pars['mask'].split(',')]
        if 'loops' in pars:
            if isinstance(pars['loops'], str):
                self.loops = [int(t) for t in pars['loops'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!midiplayer', data)


class LadspaEffect(_BankObject):

    yaml_tag = '!ladspafx'

    def __init__(self, **pars):
        super().__init__(**pars)
        if 'group' in pars:
            if isinstance(pars['group'], int):
                self.group = [pars['group']]
            elif isinstance(pars['group'], str):
                self.group = [int(t) for t in pars['group'].split(',')]
        if 'audio' in pars:
            if pars['audio'] == 'stereo':
                self.audio = 'Input L', 'Input R', 'Output L', 'Output R'
            elif pars['audio'] == 'mono':
                self.audio = 'Input', 'Output'
            elif ',' in pars['audio']:
                self.audio = [t.strip() for t in pars['audio'].split(',')]

    @staticmethod
    def to_yaml(dumper, data):
        return dumper.represent_mapping('!ladspafx', data)


def addresolver(tag, path, kind):
    BankLoader.add_path_resolver(tag, path, kind)
    BankDumper.add_path_resolver(tag, path, kind)
    BankLoader.add_path_resolver(tag, ['patches', (dict, None), *path], kind)
    BankDumper.add_path_resolver(tag, ['patches', (dict, None), *path], kind)

addresolver('!rrule', ['rules', (list, None)], dict)
addresolver('!midiplayer', ['midiplayers', (dict, None)], dict)
addresolver('!sequencer', ['sequencers', (dict, None)], dict)
addresolver('!arpeggiator', ['arpeggiators', (dict, None)], dict)
addresolver('!ladspafx', ['ladspafx', (dict, None)], dict)
addresolver('!sfpreset', [(dict, None)], str)
addresolver('!midimsg', ['messages', (list, None)], str)
addresolver('!midimsg', ['sequencers', (dict, None), 'notes', (list, None)], str)
BankLoader.add_path_resolver('!midimsg', ['init', 'messages', (list, None)], str)
BankDumper.add_path_resolver('!midimsg', ['init', 'messages', (list, None)], str)
