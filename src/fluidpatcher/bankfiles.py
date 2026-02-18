"""
Bank file parsing and validation utilities for FluidPatcher.

This module defines:
  - Custom YAML tags for expressing patches, rules, sequences, and other objects
  - Loader and dumper wrappers for FluidPatcher’s extended YAML dialect
  - Structured exceptions distinguishing syntax vs. semantic errors
  - A Bank class that represents a parsed, validated bank file
  - Helper functions for name resolution and tree walking

It enables FluidPatcher to treat YAML as a rich declarative language for
describing patches, MIDI routing, sequencing, and effects.
"""

from copy import deepcopy
import re

import yaml


TYPE_ALIAS = {}
for alts in [
    ["note", "note_on", "nt"],
    ["ctrl", "control_change", "cc"],
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
    Resolve a YAML scalar into a usable numeric value.

    Resolution rules:
      - Replace symbolic names using the ``names`` mapping
      - Convert scientific pitch notation (e.g. ``C#4`` → MIDI note 61)
      - Parse strings to integers or floats

    Args:
      s: String, integer, float, or name reference
      names (dict): Optional mapping of symbolic names to values

    Returns:
      int | float

    Raises:
      BankValidationError: if ``s`` cannot be interpreted or resolved
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
    """Base class for all bank parsing and validation errors."""
    pass
    

class BankSyntaxError(BankError):
    """
    Error raised when the YAML text is malformed and cannot be parsed.

    Attributes:
      msg (str): Reason for failure
      mark (tuple): YAML mark object describing the error
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
    Raised when a bank file is valid YAML but contains incorrect or
    unsupported values.

    Attributes:
      msg (str): Reason for failure
      path (tuple): Hierarchical path to the failing node
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
    """
    YAML loader extended with:
      - Custom tags for bank object types
      - Path and implicit resolvers
      - Construction helpers used by Bank()
    """
    pass


class BankDumper(yaml.SafeDumper):
    """
    YAML dumper that emits FluidPatcher’s extended object syntax and
    preserves key order and structure wherever possible.
    """
    pass


class Bank:
    """
    Parsed representation of a FluidPatcher bank YAML document.

    Attributes:
      root (dict):
        Raw root-level configuration data.
      patch (dict):
        Raw dictionary of patches (unmerged).
      patches (list[str]):
        Patch names in declaration order.
      soundfonts (list[SFPreset]):
        Dynamic list of soundfont files required by patches.
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

    def dump(self):
        bank = self.root | {"patches": self.patch}
        return yaml.dump(bank, Dumper=BankDumper, sort_keys=False)


class _Patch:
    """
    Lightweight merged view over root and per-patch data.

    Lookup rules:
      - Scalar fields fall back to root when absent in patch
      - Lists (rules, messages) concatenate root + patch values
      - Dict-like structures merge root defaults with overrides

    Created automatically via Bank.__getitem__.
    """

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
    """
    SoundFont preset reference

    Attributes:
      file (str): Path to the .sf2 file
      bank (int): SoundFont bank index
      prog (int): Program index
    """
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
    """
    Description of a single MIDI message

    Attributes:
      type (str): Message type (“note”, “ctrl”, “sysex”, ...)
      chan (int): Channel number (where applicable)
      num (int): Note/controller number (where applicable)
      val (int): Value (velocity, CC value, pitch bend, etc.)
    """
    yaml_tag = "!midimsg"
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(rf"^({'|'.join(TYPE_ALIAS)}):\S*$")
    zone = "messages"
    zone_type = list

    def __init__(self, **pars):
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
        match [x for x in text.split(":") if x]:
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


class _FlowList(list, yaml.YAMLObject):
    """
    Inline comma-separated list of YAML-embedded objects

    Compact list style with round-trip formatting
    """
    yaml_tag = "!flowlist"
    yaml_loader = BankLoader
    yaml_dumper = BankDumper
    yaml_regex = re.compile(r".*?,")

    @classmethod
    def from_yaml(cls, loader, node):
        text = loader.construct_scalar(node)
        obj = cls([yaml.load(e, Loader=BankLoader) for e in text.split(",")])
        obj._text = text
        return obj

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, str(data))

    def __repr__(self):
        return self._text


class _BankObject(yaml.YAMLObject):
    """
    Base class for tagged structured YAML objects inside a patch.

    Provides:
      - Storage for raw parameters as written in YAML (``_pars``)
      - Automatic deep construction of nested data
      - Validation via ``_validate``
      - Common copy/duplication support

    Subclasses define meaning, required keys, and placement
    (e.g., rules, sequences, arpeggios, etc.).
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

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping(
            cls.yaml_tag,
            data,
            flow_style=cls.yaml_flow_style
        )

    def _init_pars(self, pars):
        self.__dict__.update(pars)
        self._pars = pars

    def copy(self, **pars):
        for k, v in self.__dict__.items():
            if k[0] != "_":
                pars.setdefault(k, v)
        return self.__class__(**pars)

    def _validate(self, path=(), names={}):
        for k, v in self.__dict__.items():
            if k[0] != "_":
                _walk(v, path + (k,), names)

    def __repr__(self):
        return str(self._pars)

    def __iter__(self):
        return iter([(k, v) for k, v in self._pars.items()])


class MidiRule(_BankObject):
    """
    A mapping that describes how to match incoming MIDI messages and
    what events they should trigger.

    Attributes:
      type (str): Matching message type
      totype (str): Resulting message type (default: ``self.type``)
      chan (Route): Channel range/transform (optional)
      num (Route): Parameter range/transform (optional)
      val (Route): Value range/transform (optional)
      **pars (dict): additional parameters for custom functionality
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
                setattr(self, par, Route.from_ranges(min, max, tomin, tomax))
            elif m := self.maroute.match(spec):
                min, max, mul, add = [resolve(x, names) for x in m.groups()]
                setattr(self, par, Route.from_affine(min, max, mul, add))
        if hasattr(self, "lsb"):
            self.lsb = resolve(self.lsb, names)

    def __str__(self):
        return ", ".join([f"{k}: {v}" for k, v in self._pars.items()])


class Route:
    """
    An object that expresses MIDI parameter ranges/transforms.

    Attributes:
      min (int|float): minimum value to match
      max (int|float): maximum value to match
      mul (int|float): multiplier to apply to values
      add (int|float): amount to add to values
      tomin (int|float): minimum of target range for values
      tomax (int|float): maximum of target range for values
    """
    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add
        self.tomin = min * mul + add
        self.tomax = max * mul + add

    @classmethod
    def from_ranges(cls, min=None, max=None, tomin=None, tomax=None):
        """
        Creates a Route based on from-to ranges

        Args:
          min (int|float): minimum value to match
          max (int|float): maximum value to match
          tomin (int|float): minimum of target range for values
          tomax (int|float): maximum of target range for values
        """
        if min is None:
            min, max = 0, 127
        elif max is None:
            max = min
        if tomin is None:
            tomin, tomax = min, max
        elif tomax is None:
            tomax = tomin
        mul = 1 if min == max else (tomax - tomin) / (max - min)
        add = tomin - min * self.mul
        obj = cls(min, max, mul, add)
        obj.tomin = tomin
        obj.tomax = tomax
        return obj

    @classmethod
    def from_affine(cls, min, max, mul, add):
        """
        Creates a Route using an affine transform

        Args:
          min (int|float): minimum value to match
          max (int|float): maximum value to match
          mul (int|float): multiplier to apply to values
          add (int|float): amount to add to values
        """
        return cls(min, max, mul, add)

    def __iter__(self):
        tovals = range(self.tomin, self.tomax + 1)
        return iter(
            Route.from_ranges(self.min, self.max, n, n) for n in tovals
        )


class Sequence(_BankObject):
    """
    Step-sequenced event container

    Attributes:
      events (list): Parsed events grouped by pattern
      order (list): Playback order of patterns (default: ``[1]``)
      tempo (int): Beats per minute (default: ``120``)
      tdiv (int): Beat divisor (default: ``8``)
      swing (float): Timing swing ratio (default: ``0.5``)
      groove (int|list): Beat accent pattern (default: ``[1, 1]``)
    """
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


class Arpeggio(_BankObject):
    """
    Patterned arpeggiation definition

    Attributes:
      style (str): Pattern type
      tempo (int): Beats per minute (default: ``120``)
      tdiv (int): Beat divisor (default: ``8``)
      swing (float): Timing swing ratio (default: ``0.5``)
      groove (int|list): Beat accent pattern (default: ``[1, 1]``)
    """
    yaml_tag = "!arpeggio"
    zone = "arpeggios"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "style"):
            raise BankValidationError("Arpeggio missing style")
        if hasattr(self, "groove"):
            if isinstance(self.groove, int):
                self.groove = [self.groove, 1]


class MidiLoop(_BankObject):
    """
    Looping MIDI event generator

    Attributes:
      beats (int): Loop length in beats
      tempo (int): Beats per minute (default: ``120``)
    """
    yaml_tag = "!midiloop"
    zone = "midiloops"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "beats"):
            raise BankValidationError("MidiLoop objects must have beats")


class MidiFile(_BankObject):
    """
    MIDI file playback directive

    Attributes:
      file (str): Path to a .mid file
      tempo (int): Beats per minute (default: ``120``)
      barlength (int): Ticks per musical measure (default: ``1``)
      jumps (list[str]): List of bar jumps as [from]>[to] (default: ``[]``)
      shift (int): Channel shift amount (default: ``0``)
      mask (list[str]): Ignored message types (default: ``[]``) 
    """
    yaml_tag = "!midifile"
    zone = "midifiles"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "file"):
            raise BankValidationError("MidiFile missing file")
        if hasattr(self, "jumps"):
            if isinstance(self.jumps, str):
                self.jumps = [self.jumps]
            self.jumps = [
                [float(t) for t in s.split(">")] for s in self.jumps
            ]
        if hasattr(self, "mask"):
            self.mask = [TYPE_ALIAS[t] for t in self.mask]

class LadspaEffect(_BankObject):
    """
    LADSPA audio effect declaration

    Attributes:
      lib (str): LADSPA library basename
      plugin (str): Plugin label (default: ``''``)
      audio (list[str]): Audio port names (default: ``['Input', 'Output']``)
      vals (dict): Initial values for control ports (default: ``{}``)
      chan (list[int]): Input channel routing (default: ``[]``)
    """
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


class Counter(_BankObject):
    """
    State storing object that responds to messages/rules

    Attributes:
      min/max (float): range for values
      startval (float): Initial value for counter (default: ``self.min``)
      wrap (bool): wrap values if True, else clamp to range (default: ``False``)
    """
    yaml_tag = "!counter"
    zone = "counters"
    zone_type = dict

    def _validate(self, path=(), names={}):
        super()._validate(path, names)
        if not hasattr(self, "min"):
            raise BankValidationError("Counter objects must have min")
        if not hasattr(self, "max"):
            raise BankValidationError("Counter objects must have max")
        if not hasattr(self, "startval"):
            self.startval = self.min
        if not hasattr(self, "wrap"):
            self.wrap = False

def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

yaml.add_representer(str, str_presenter, Dumper=BankDumper)

for cls in (SFPreset, MidiMessage, _FlowList):
    BankLoader.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)
    BankDumper.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)

for cls in _BankObject.__subclasses__():
    path = ["patches", (dict, None), cls.zone, (cls.zone_type, None)]
    BankLoader.add_path_resolver(cls.yaml_tag, path, dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path, dict)
    BankLoader.add_path_resolver(cls.yaml_tag, path[2:], dict)
    BankDumper.add_path_resolver(cls.yaml_tag, path[2:], dict)

