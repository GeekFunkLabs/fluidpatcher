"""YAML extensions for fluidpatcher"""

from copy import deepcopy
import re

import yaml


TYPE_ALIAS = {}
for alts in [
    ["note", "note_on", "nt"],
    ["cc", "control_change"],
    ["prog", "program_change", "pc"],
    ["pbend", "pitchwheel", "pb"],
    ["cpress", "aftertouch", "cp"],
    ["kpress", "polytouch", "kp"],
    ["sysex"],
    ["clock"],
    ["start"],
    ["continue"],
    ["stop"],
]:
    for a in alts:
        TYPE_ALIAS[a] = alts[0]

scinote = re.compile(r"([+-]?)([A-G])([b#]?)(-?[0-9])")

def resolve(s, names={}):
    """
    convert scientific note names to numbers
    perform name resolution
    convert strings to float, int
    """
    if s in names:
        s = names[s]
    if isinstance(s, str):
        if sci := scinote.match(s):
            sci = sci.groups("")
            sign = -1 if sci[0] == "-" else 1
            note = "C D EF G A B".find(sci[1])
            acc = ["b", "", "#"].index(sci[2]) - 1
            octave = int(sci[3])
            s = sign * ((octave + 1) * 12 + note + acc)
        else:
            try:
                s = float(s)
            except (ValueError, TypeError):
                raise BankValidationError(f"Unresolved name '{s}'")
            else:
                if s.is_integer():
                    s = int(s)
    return s

def _walk(node, path=(), names={}):
    if node is None:
        raise BankValidationError(
            "Null value in bank", path
        )
    if hasattr(node, "_validate"):
        try:
            node._validate(path, names)
        except BankValidationError as e:
            e.path = path + e.path[len(path):]
            raise(e)
        except Exception as e:
            raise BankValidationError(str(e), path)
    elif isinstance(node, dict):
        for k, v in node.items():
            _walk(v, path + (k,), names)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, path + (i,), names)


class BankError(Exception):
    pass
    

class BankSyntaxError(BankError):
    """
    Raised when YAML can't be parsed
    """
    def __init__(self, msg):
        self.msg = msg
        self.mark = None

    @classmethod
    def from_yamlexc(cls, exc):
        """
        Wraps a YAMLError and extracts info about
        the location and reason
        """
        obj = cls.__new__(cls)
        obj.msg = (
            getattr(exc, "context", None) or
            getattr(exc, "problem", None) or
            str(exc)
        )
        obj.mark = (
            getattr(exc, "context_mark", None) or
            getattr(exc, "problem_mark", None) or
            None
        )
        return obj

    def __str__(self):
        if self.mark:
            loc = f" at line {self.mark.line}, column {self.mark.column}"
        else:
            loc = ""
        return self.msg + loc    


class BankValidationError(BankError):
    """
    Raised when a bank file is structurally valid YAML
    but contains invalid or unsupported data.
    """
    def __init__(self, msg, path=()):
        self.msg = msg
        self.path = path

    def __str__(self):
        if self.path:
            loc = " in " + ".".join(map(str, self.path))
        else:
            loc = ""
        return self.msg + loc


class BankLoader(yaml.SafeLoader):
    pass


class BankDumper(yaml.SafeDumper):
    pass


class Bank:
    """
    Parsed representation of a bank YAML file.

    Behaves like a mapping of patch names to fully-resolved data.

    Attributes and access patterns:
      - self[patch_name] – merged view combining root-level defaults with
        the patch’s own data.
      - self.root – raw root-level settings shared by all patches.
      - self.patch – raw per-patch data without root merging.
      - self.patches – sequence of defined patch names in declaration order.
    """
    def __init__(self, text):
        try:
            self.root = yaml.load(text, Loader=BankLoader)
        except yaml.YAMLError as e:
            raise BankSyntaxError.from_yamlexc(e)
        self.patch = self.root.setdefault("patches", {})
        names = self.root.get("names", {})
        _walk(self.root, path=(), names=names)

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
        bank = self.root | {"patches": self.patch}
        return yaml.dump(bank, Dumper=BankDumper, sort_keys=False)


class _Patch:

    def __init__(self, root, patch):
        self._patch = patch
        self._root = root
        
    def __getitem__(self, name):    
        if isinstance(name, int):
            return self._patch.get(name) or self._root.get(name)
        elif name in ("rules", "messages"):
            return self._root.get(name, []) + self._patch.get(name, [])
        else:
            return self._root.get(name, {}) | self._patch.get(name, {})

    def copy(self, **pars):
        return deepcopy(self._patch | pars)


class SFPreset(yaml.YAMLObject):

    yaml_tag = "!sfpreset"
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(r"^(.+\.sf2):(\d+):(\d+)$", flags=re.I)
    zone = None

    def __init__(self, file, bank, prog):
        self.file = file
        self.bank = int(bank)
        self.prog = int(prog)

    @classmethod
    def from_yaml(cls, loader, node):
        return cls(*loader.construct_scalar(node).split(":"))

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))

    def __repr__(self):
        return f"{self.file}:{self.bank:03d}:{self.prog:03d}"


class MidiMessage(yaml.YAMLObject):
    """Class for describing and storing MIDI messages
    """
    
    yaml_tag = "!midimsg"
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(rf"^({"|".join(TYPE_ALIAS)}):\S*$")
    zone = "messages"
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
        if "_text" not in pars:
            match pars:
                case {"type": "sysex", "val": data}:
                    self._text = ":".join(["sysex"] + [str(b) for b in data])
                case {"type": type, "chan": chan, "num": num, "val": val}:
                    self._text = f"{type}:{chan}:{num}:{val}"
                case {"type": type, "chan": chan, "val": val}:
                    self._text = f"{type}:{chan}:{val}"
                case {"type": type}:
                    self._text = type
        self._validate()

    @classmethod
    def from_yaml(cls, loader, node):
        text = loader.construct_scalar(node)
        match text.split(":"):
            case ["sysex", *data]:
                pars = dict(type="sysex", val=data)
            case [type, chan, num, val]:
                pars = dict(type=type, chan=chan, num=num, val=val)
            case [type, chan, val]:
                pars = dict(type=type, chan=chan, val=val)
            case [type]:
                pars = dict(type=type, _text=text)
        obj = cls.__new__(cls)
        obj.__dict__.update(pars)
        obj._pars = pars
        obj._text = text
        return obj
        
    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))
            
    def copy(self, **pars):
        return MidiMessage(**self.__dict__ | pars)

    def _validate(self, path=(), names={}):
        if not hasattr(self, "type"):
            raise BankValidationError("MidiMessage missing type")
        self.type = TYPE_ALIAS[self.type]
        for par in "chan", "num", "val":
            if hasattr(self, par):
                setattr(self, par, resolve(getattr(self, par), names))

    def __repr__(self):
        return self._text


class _BankObject(yaml.YAMLObject):
    """metaclass for mapping-type Bank data
    
    Attributes:
      _pars: exact parameters as written in bank file, read-only
      pars: copy of opars with elements modified as needed
    """

    yaml_loader = BankLoader
    yaml_dumper = BankDumper

    def __init__(self, **pars):
        self._init_pars(pars)
        self._validate()

    @classmethod
    def from_yaml(cls, loader, node):
        pars = loader.construct_mapping(node, deep=True)
        obj = cls.__new__(cls)
        obj._init_pars(pars)
        return obj

    def _init_pars(self, pars):
        self.__dict__.update(pars)
        self._pars = pars

    def copy(self, **pars):
        pars["_pars"] = self._pars | pars
        return self.__class__(**self.__dict__ | pars)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping(
            cls.yaml_tag,
            data,
            flow_style=cls.yaml_flow_style
        )

    def _validate(self, path=(), names={}):
        for k, v in self:
            _walk(v, path + (k,), names)

    def __repr__(self):
        return str(self._pars)

    def __contains__(self, k):
        return k in self.__dict__

    def __iter__(self):
        return iter(
            [(k, v) for k, v in self.__dict__.items() if k[0] != "_"]
        )


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


class MidiRule(_BankObject):
    """Class that describes responses to MIDI messages
    
    Attributes:
      type: MIDI message types to match
      totype: MIDI event type to produce
      chan, num, val: expressions describing the range of the
        corresponding message parameter to accept, and how to
        modify the parameter in the result.
      arbitrary additional parameters can be given as keyword arguments
    """
    ftroute = re.compile(r"^({0})?-?({0})?=?(-?{0})?-?(-?{0})?$".format(r"[\w\d\#\.]+"))
    maroute = re.compile(r"^({0})-({0})\*(-?{0})([+-]{0})$".format(r"[\w\d\#\.]+"))
    yaml_tag = "!midirule"
    yaml_flow_style = True
    zone = "rules"
    zone_type = list

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "type"):
            raise BankValidationError("MidiRule missing type")
        if not hasattr(self, "totype"):
            types = self.type.split("=")
            for type in types:
                if type not in TYPE_ALIAS:
                    raise BankValidationError(
                        f"MidiRule type '{type}' not recognized"
                    )
            self.type = TYPE_ALIAS[types[0]]
            self.totype = TYPE_ALIAS[types[-1]]
        for par in "chan", "num", "val":
            spec = str(getattr(self, par, ""))
            if (m := self.ftroute.match(spec)) and any(m.groups()):
                min, max, tomin, tomax = [resolve(x, names) for x in m.groups()]
                if min == None:
                    min, max = (1, 256) if par == "chan" else (1, 127)
                elif max == None:
                    max = min
                if tomin == None:
                    tomin, tomax = min, max
                elif tomax == None:
                    tomax = tomin
                setattr(self, par, _Route(min, max, tomin, tomax))
            elif m := self.maroute.match(spec):
                min, max, mul, add = [resolve(x, names) for x in m.groups()]
                tomin = min * mul + add
                tomax = max * mul + add
                setattr(self, par, _Route(min, max, tomin, tomax, mul, add))

    def __str__(self):
        return ", ".join([f"{k}: {v}" for k, v in self._pars.items()])


class _FlowList(list, yaml.YAMLObject):

    yaml_tag = "!flowlist"
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(r".*?,")

    @classmethod
    def from_yaml(cls, loader, node):
        text = loader.construct_scalar(node)
        obj = cls([yaml.load(e, Loader=BankLoader) for e in text.split(",")])
        obj.text = text
        return obj

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))

    def __repr__(self):
        return self.text


class Sequence(_BankObject):

    yaml_tag = "!sequence"
    zone = "sequences"
    zone_type = dict

    def _init_pars(self, pars):
        super()._init_pars(pars)
        if "\n" in getattr(self, "events", ""):
            events = []
            for p in self.events.strip().split("\n\n"):
                s = [[yaml.load(e, Loader=BankLoader) for e in r.split()]
                     for r in p.splitlines()]
                events.append([list(t) for t in zip(*s)])
            self.events = events

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "events"):
            raise BankValidationError("Sequence objects must have events")
        if hasattr(self, "groove"):
            if isinstance(self.groove, int):
                self.groove = [self.groove, 1]


class Arpeggio(_BankObject):

    yaml_tag = "!arpeggio"
    zone = "arpeggios"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "style"):
            raise BankValidationError("Arpeggio missing style")


class MidiLoop(_BankObject):

    yaml_tag = "!midiloop"
    zone = "midiloops"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "beats"):
            raise BankValidationError("MidiLoop objects must have beats")


class MidiFile(_BankObject):

    yaml_tag = "!midifile"
    zone = "midifiles"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "file"):
            raise BankValidationError("MidiFile missing file")
        if hasattr(self, "jumps"):
            self.jumps = [
                [int(t) for t in s.split(">")] for s in self.jumps
            ]


class LadspaEffect(_BankObject):

    yaml_tag = "!ladspafx"
    zone = "ladspafx"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "lib"):
            raise BankValidationError("LadspaEffect missing lib")
        if hasattr(self, "chan"):
            if not isinstance(self.chan, list):
                self.chan = [self.chan]
        if hasattr(self, "audio"):
            if self.audio == "stereo":
                self.audio = "Input L", "Input R", "Output L", "Output R"
            elif self.audio == "mono":
                self.audio = "Input", "Output"


def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

yaml.add_representer(str, str_presenter, Dumper=BankDumper)

for cls in _BankObject.__subclasses__():
    path = ["patches", (dict, None), cls.zone, (cls.zone_type, None)]
    BankLoader.add_path_resolver(cls.yaml_tag, path, dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path, dict)
    BankLoader.add_path_resolver(cls.yaml_tag, path[-2:], dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path[-2:], dict)

for cls in (SFPreset, MidiMessage, _FlowList):
    BankLoader.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)
    BankDumper.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)

