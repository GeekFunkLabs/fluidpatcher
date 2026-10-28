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
from pathlib import Path
import re

import yaml

from .config import CONFIG


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

MIDI_NOTES = {}
for octave in range(-1, 10):
    for name, base in zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)):
        for acc, inc in (("", 0), ("#", 1), ("b", -1)):
            midi = (octave + 1) * 12 + base + inc
            if 0 <= midi <= 127:
                MIDI_NOTES[f"{name}{acc}{octave}"] = midi

def _resolve(s, names=None):
    if names is not None and s in names:
        s = names[s]
    if s in MIDI_NOTES:
        s = MIDI_NOTES[s]
    if isinstance(s, str):
        try:
            s = float(s)
        except (ValueError, TypeError):
            raise BankValidationError(f"Unresolved name '{s}'")
        else:
            if s.is_integer():
                s = int(s)
    return s

def _resolved_property(par):
    def getter(obj):
        return obj.__dict__.get(par)
    def setter(obj, val):
        obj.__dict__[par] = _resolve(val)
    return property(getter, setter)

def _int_property(par):
    def getter(obj):
        return obj.__dict__.get(par)
    def setter(obj, val):
        obj.__dict__[par] = int(val)
    return property(getter, setter)

def _walk(node, path=None, names=None):
    if path is None:
        path = ()
    if node is None:
        raise BankValidationError(
            "Null value in bank", path
        )
    if isinstance(node, _BankObject):
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

def _load_yaml(text, path=None):
    print(f"{path}:\n{text}\n\n")
    loader = _BankLoader(text)
    loader.source_path = (
        Path(path).resolve() if path is not None else None
    )
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


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
    def __init__(self, msg, path=None):
        self.msg = msg
        self.path = () if path is None else path

    def __str__(self):
        if self.path:
            loc = " in " + ".".join(map(str, self.path))
        else:
            loc = ""
        return self.msg + loc


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
    def __init__(self, text, path=None):
        if path is not None:
            path = CONFIG["banks_path"] / Path(path).expanduser()
        if text is None:
            text = path.read_text()
        try:
            self.root = _load_yaml(text, path=path)
        except yaml.YAMLError as e:
            raise BankSyntaxError.from_yamlexc(e)
        self.patch = self.root.setdefault("patches", {})
        names = self.root.get("names", {})
        _walk(self.root, names=names)

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
        return yaml.dump(bank, Dumper=_BankDumper, sort_keys=False)


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
        
    def __getitem__(self, zone):
        if isinstance(zone, int):
            return self._patch.get(zone) or self._root.get(zone)
        elif name in ("rules", "messages"):
            return self._root.get(zone, []) + self._patch.get(zone, [])
        else:
            return self._root.get(zone, {}) | self._patch.get(zone, {})

    def copy(self, **pars):
        return deepcopy(self._patch | pars)


class _BankLoader(yaml.SafeLoader):
    """
    YAML loader extended with:
      - Custom tags for bank object types
      - Path and implicit resolvers
      - Construction helpers used by Bank()
    """
    pass


class _BankDumper(yaml.SafeDumper):
    """
    YAML dumper that emits FluidPatcher’s extended object syntax and
    preserves key order and structure wherever possible.
    """
    def _is_bankscalar(self, event):
        if not isinstance(event, yaml.events.ScalarEvent):
            return False
        for cls in _BankObject.__subclasses__():
            if (
                hasattr(cls, "yaml_regex")
                and event.tag == cls.yaml_tag
                and cls.yaml_regex.fullmatch(event.value)
            ):
                return True
        return False

    def choose_scalar_style(self):
        if (
            self.flow_level
            and not self.simple_key_context
            and not self.event.style
            and self._is_bankscalar(self.event)
        ):
            return ""
        return super().choose_scalar_style()

    def process_tag(self):
        if self.flow_level and self._is_bankscalar(self.event):
            self.prepared_tag = None
            return
        super().process_tag()


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
    required = ()
    yaml_loader = _BankLoader
    yaml_dumper = _BankDumper
    _flow_style = None

    def __init__(self, **pars):
        self._source = deepcopy(pars)
        self.__dict__.update(deepcopy(pars))
        self._validate()

    @classmethod
    def from_yaml(cls, loader, node):
        obj = cls.__new__(cls)
        obj._source = loader.construct_mapping(node, deep=True)
        obj.__dict__.update(deepcopy(obj._source))
        obj._flow_style = node.flow_style
        return obj

    @property
    def current(self):
        return {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }

    @property
    def validated(self):
        return getattr(self, "_validated", False)

    def _validate(self, path=None, names=None):
        if path is None:
            path = ()
        for par in self.required:
            if par not in self.__dict__:
                raise BankValidationError(
                    f"{self.__class__.__name__} objects must have {par}"
                )
        for k, v in self.current.items():
            _walk(v, path + (k,), names)
        self._subvalidate(path, names)
        self._validated = deepcopy(self.current)

    def _subvalidate(self, path, names):
        pass

    def __str__(self):
        return str(self.current)

    def __repr__(self):
        return f"<{self.__class__.__name__} {str(self)}>"

    def __eq__(self, other):
        return self.current == other.current

    def copy(self, **pars):
        return self.__class__(**self.current | pars)

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.validated and data.current != data.validated:
            rep = data.current
        else:
            rep = data._source
        return dumper.represent_mapping(
            cls.yaml_tag,
            rep,
            flow_style=data._flow_style
        )


class SFPreset(_BankObject):
    """
    SoundFont preset reference

    Attributes:
      file (str): Path to the .sf2 file
      bank (int): SoundFont bank index
      prog (int): Program index
    """
    required = ("file", "bank", "prog")
    yaml_tag = "!sfpreset"
    yaml_regex = re.compile(r"^(.+\.sf2):(\d+):(\d+)$", flags=re.I)
    bank = _int_property("bank")
    prog = _int_property("prog")

    def __init__(self, file, bank, prog):
        self.file = file
        self.bank = bank
        self.prog = prog
        self._source = str(self)
        self._validate()    

    @classmethod
    def from_yaml(cls, loader, node):
        obj = cls.__new__(cls)
        obj._source = loader.construct_scalar(node)
        obj.file, obj.bank, obj.prog = obj._source.split(":")
        return obj

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.validated and data.current != data.validated:
            return dumper.represent_scalar(cls.yaml_tag, str(data))
        else:
            return dumper.represent_scalar(cls.yaml_tag, data._source)

    def __str__(self):
        return f"{self.file}:{self.bank:03d}:{self.prog:03d}"


class MidiMessage(_BankObject):
    """
    Description of a single MIDI message

    Attributes:
      type (str): Message type (“note”, “ctrl”, “sysex”, ...)
      chan (int): Channel number (where applicable)
      num (int): Note/controller number (where applicable)
      val (int): Value (velocity, CC value, pitch bend, etc.)
    """
    required = "type",
    yaml_tag = "!midimsg"
    yaml_regex = re.compile(rf"^({'|'.join(TYPE_ALIAS)}):\S*$")
    chan = _int_property("chan")
    num = _resolved_property("num")
    val = _int_property("val")

    def __init__(self, **pars):
        self.__dict__.update(pars)
        self._source = str(self)
        self._validate()

    @property
    def type(self):
        return self.__dict__["type"]

    @type.setter
    def type(self, type):
        if type not in TYPE_ALIAS:
            raise BankValidationError(
                f"{self.__class__.__name__} type {type!r} not recognized"
            )
        self.__dict__["type"] = TYPE_ALIAS[type]

    @classmethod
    def from_yaml(cls, loader, node):
        obj = cls.__new__(cls)
        obj._source = loader.construct_scalar(node)
        match [x for x in obj._source.split(":") if x]:
            case ["sysex", *data]:
                pars = dict(type="sysex", val=[int(y, 0) for y in data])
            case [type, chan, num, val]:
                pars = dict(type=type, chan=chan, num=num, val=val)
            case [type, chan, val]:
                pars = dict(type=type, chan=chan, val=val)
            case [type]:
                pars = dict(type=type)
        obj.__dict__.update(pars)
        return obj

    def _subvalidate(self, path=None, names=None):
        self.type = self.__dict__["type"]
        for par in "chan", "num", "val":
            val = self.__dict__.get(par)
            if val is not None:
                self.__dict__[par] = _resolve(val, names)

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.validated and data.current != data.validated:
            return dumper.represent_scalar(cls.yaml_tag, str(data))
        else:
            return dumper.represent_scalar(cls.yaml_tag, data._source)

    def __str__(self):
        match self.current:
            case {"type": "sysex", "val": data}:
                return ":".join(["sysex"] + [str(b) for b in data])
            case {"type": type, "chan": chan, "num": num, "val": val}:
                return f"{type}:{chan}:{num}:{val}"
            case {"type": type, "chan": chan, "val": val}:
                return f"{type}:{chan}:{val}"
            case {"type": type}:
                return type


class MidiRule(_BankObject):
    """
    A mapping that describes how to match incoming MIDI messages and
    what events they should trigger.

    Attributes:
      type (str): Matching message type
      totype (str): Resulting message type (default: ``self.type``)
      chan (_Route): Channel range/transform (optional)
      num (_Route): Parameter range/transform (optional)
      val (_Route): Value range/transform (optional)
      **pars (dict): additional parameters for custom functionality
    """
    def _route_property(par):
        def getter(self):
            return self.__dict__.get(par)
        def setter(self, spec):
            self._set_route(par, spec)
        return property(getter, setter)

    required = "type",
    NN = r"[\w#.]+" # number or note name regex
    re_range = re.compile(rf"({NN})-?({NN})?=?(-?{NN})?-?(-?{NN})?")
    re_affine = re.compile(rf"({NN})-({NN})\*(-?{NN})([+-]{NN})")
    yaml_tag = "!midirule"
    _flow_style = True
    zone = "rules"
    zone_type = list
    chan = _route_property("chan")
    num = _route_property("num")
    val = _route_property("val")

    @property
    def type(self):
        return f"{self.__dict__['type']}={self.totype}"

    @type.setter
    def type(self, spec):
        types = spec.split("=")
        for type in types:
            if type not in TYPE_ALIAS:
                raise BankValidationError(
                    f"{self.__class__.__name__} type {type!r} not recognized"
                )
        self.__dict__["type"] = TYPE_ALIAS[types[0]]
        self.totype = TYPE_ALIAS[types[-1]]

    def _set_route(self, par, spec, names=None):
        if spec is None:
            self.__dict__.pop(par, None)
            return
        if m := self.re_range.fullmatch(str(spec)):
            values = [_resolve(x, names) for x in m.groups()]
            self.__dict__[par] = _Route(*values)
        elif m := self.re_affine.fullmatch(str(spec)):
            values = [_resolve(x, names) for x in m.groups()]
            self.__dict__[par] = _Route.from_affine(*values)
        else:
            raise BankValidationError(
                f"Invalid {par} route {spec!r}"
            )

    def _subvalidate(self, path=None, names=None):
        self.type = self.__dict__["type"]
        for par in "chan", "num", "val":
            spec = self.__dict__.get(par)
            self._set_route(par, spec, names)
        if hasattr(self, "lsb"):
            self.lsb = _resolve(self.lsb, names)

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.validated and data.current != data.validated:
            rep = data.current | {
                par: str(spec) for par, spec in data.current.items()
                if par in ("chan", "num", "val")
            }
        else:
            rep = data._source
        return dumper.represent_mapping(
            cls.yaml_tag, rep, flow_style = data._flow_style
        )


class _Route:
    """
    An object that expresses MIDI parameter ranges/transforms.

    Attributes:
      min (int|float): minimum value to match
      max (int|float): maximum value to match
      tomin (int|float): minimum of target range for values
      tomax (int|float): maximum of target range for values
      mul (int|float): multiplier to apply to values
      add (int|float): amount to add to values
    """

    min = _resolved_property("min")
    max = _resolved_property("max")
    tomin = _resolved_property("tomin")
    tomax = _resolved_property("tomax")

    def __init__(self, min, max, tomin, tomax):
        """
        Creates a _Route based on from-to ranges

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
        self.min = min
        self.max = max
        self.tomin = tomin
        self.tomax = tomax

    @property
    def mul(self):
        if self.min == self.max:
            return 1
        else:
            return (self.tomax - self.tomin) / (self.max - self.min)

    @mul.setter
    def mul(self, val):
        self.tomin = self.min * _resolve(val) + self.add
        self.tomax = self.max * _resolve(val) + self.add

    @property
    def add(self):
        return self.tomin - self.min * self.mul

    @add.setter
    def add(self, val):
        self.tomin = self.min * self.mul + _resolve(val)
        self.tomax = self.max * self.mul + _resolve(val)

    @classmethod
    def from_affine(cls, min, max, mul, add):
        """
        Creates a _Route using an affine transform

        Args:
          min (int|float): minimum value to match
          max (int|float): maximum value to match
          mul (int|float): multiplier to apply to values
          add (int|float): amount to add to values
        """
        obj = cls(min, max, min * mul + add, max * mul + add)
        return obj

    def __repr__(self):
        spec = f"{self.min}"
        if self.max != self.min: spec += f"-{self.max}"
        tospec = f"{self.tomin}"
        if self.tomax != self.tomin: tospec += f"-{self.tomax}"
        if tospec != spec: spec += f"={tospec}"
        return spec

    def __eq__(self, other):
        if not isinstance(other, _Route):
            return NotImplemented
        return (
            self.min == other.min
            and self.max == other.max
            and self.tomin == other.tomin
            and self.tomax == other.tomax
        )

    def __iter__(self):
        tovals = range(int(self.tomin), int(self.tomax) + 1)
        return iter(
            _Route.from_ranges(self.min, self.max, n, n) for n in tovals
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
    required = "events",
    yaml_tag = "!sequence"
    zone = "sequences"
    zone_type = dict

    @classmethod
    def from_yaml(cls, loader, node):
        obj = cls.__new__(cls)
        obj._source = loader.construct_mapping(node, deep=True)
        obj.__dict__.update(deepcopy(obj._source))
        if isinstance(obj.events, str):
            events = []
            for p in obj.events.strip().split("\n\n"):
                s = [[yaml.load(e, Loader=_BankLoader) for e in r.split()]
                     for r in p.splitlines()]
                events.append([list(t) for t in zip(*s)])
            obj.__dict__["events"] = events
        obj._flow_style = node.flow_style
        return obj

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.validated and data.current != data.validated:
            if data.events == data.validated["events"]:
                rep = data.current
            else:
                patterns = []
                for tracks in data.events:
                    patterns.append("\n".join(
                        "  ".join(f"{str(e):>18}" for e in row)
                        for row in zip(*tracks)
                    ))
                rep = data.current | {"events": "\n\n".join(patterns)}
        else:
            rep = data._source
        return dumper.represent_mapping(
            cls.yaml_tag, rep, flow_style=data._flow_style
        )


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
    required = "style",
    yaml_tag = "!arpeggio"
    zone = "arpeggios"
    zone_type = dict


class MidiLoop(_BankObject):
    """
    Looping MIDI event generator

    Attributes:
      beats (int): Loop length in beats
      tempo (int): Beats per minute (default: ``120``)
    """
    required = "beats",
    yaml_tag = "!midiloop"
    zone = "midiloops"
    zone_type = dict


class MidiFile(_BankObject):
    """
    MIDI file playback directive

    Attributes:
      file (str): Path to a .mid file
      tempo (int): Beats per minute (default: ``120``)
      barlength (int): Ticks per musical measure (default: ``1``)
      jumps (list[str]): List of bar jumps as <from>><to> (default: ``[]``)
      shift (int): Channel shift amount (default: ``0``)
      mask (list[str]): Ignored message types (default: ``[]``) 
    """
    required = "file",
    yaml_tag = "!midifile"
    zone = "midifiles"
    zone_type = dict

    @property
    def jumps(self):
        return self.__dict__["jumps"]

    @jumps.setter
    def jumps(self, val):
        self.__dict__["jumps"] = [
            [float(bar) for bar in j.split(">")] for j in val
        ]

    @property
    def mask(self):
        return self.__dict__["mask"]

    @mask.setter
    def mask(self, val):
        for type in val:
            if type not in TYPE_ALIAS:
                raise BankValidationError(
                    f"MIDI message type {type!r} not recognized"
                )
        self.__dict__["mask"] = [TYPE_ALIAS[t] for t in val]

    def _subvalidate(self, path=None, names=None):
        if "jumps" in self.__dict__:
            self.jumps = self.__dict__["jumps"]
        if "mask" in self.__dict__:
            self.mask = self.__dict__["mask"]

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
    required = "lib",
    yaml_tag = "!ladspafx"
    zone = "ladspafx"
    zone_type = dict

    @property
    def audio(self):
        return self.__dict__["audio"]

    @audio.setter
    def audio(self, val):
        if val == "stereo":
            val = "Input L", "Input R", "Output L", "Output R"
        elif val == "mono":
            val = "Input", "Output"
        self.__dict__["audio"] = val

    def _subvalidate(self, path=None, names=None):
        if "audio" in self.__dict__:
            self.audio = self.__dict__["audio"]


class Counter(_BankObject):
    """
    State storing object that responds to messages/rules

    Attributes:
      min/max (float): range for values
      startval (float): Initial value for counter (default: ``self.min``)
      wrap (bool): wrap values if True, else clamp to range (default: ``False``)
    """
    required = "min", "max"
    yaml_tag = "!counter"
    zone = "counters"
    zone_type = dict

    def _subvalidate(self, path=None, names=None):
        if not hasattr(self, "startval"):
            self.startval = self.min
        if not hasattr(self, "wrap"):
            self.wrap = False


# Make plain lists/dicts retain flow style
class _BankList(list):
    @staticmethod
    def construct(loader, node):
        data = _BankList()
        yield data
        data.extend(loader.construct_sequence(node))
        data._flow_style = node.flow_style

    @staticmethod
    def represent(dumper, data):
        return dumper.represent_sequence("tag:yaml.org,2002:seq",
            data, flow_style=data._flow_style)


class _BankDict(dict):
    @staticmethod
    def construct(loader, node):
        data = _BankDict()
        yield data
        data.update(loader.construct_mapping(node))
        data._flow_style = node.flow_style

    @staticmethod
    def represent(dumper, data):
        return dumper.represent_mapping("tag:yaml.org,2002:map",
            data, flow_style=data._flow_style)


class _IncludedList(_BankList):
    pass


class _IncludedDict(_BankDict):
    pass


def _construct_include(loader, node):
    filename = loader.construct_scalar(node)
    paths = [Path(filename).expanduser()]
    if not paths[0].is_absolute():
        paths = [CONFIG["banks_path"] / filename]
        if loader.source_path is not None:
            paths.append(loader.source_path.parent / filename)
    for path in paths:
        if path.is_file():
            data = _load_yaml(path.read_text(), path=path)
            if isinstance(data, list):
                obj = _IncludedList()
                yield obj
                obj.extend(data)
            elif isinstance(data, dict):
                obj = _IncludedDict()
                yield obj
                obj.update(data)
            obj._original = deepcopy(data)
            obj._flow_style = data._flow_style
            obj._source = filename
            break
    else:
        raise FileNotFoundError(
            f"Include file {obj._source} not found. Searched:",
            *(f"\n  {p}" for p in paths)
        )

def _represent_include(dumper, data):
    if data != data._original:
        if isinstance(data, _IncludedList):
            return dumper.represent_sequence(
                "tag:yaml.org,2002:seq",
                data, flow_style=data._flow_style,
            )
        elif isinstance(data, _IncludedDict):
            return dumper.represent_mapping(
                "tag:yaml.org,2002:map",
                data, flow_style=data._flow_style,
            )
        else:
            raise TypeError("Unable to represent {type(data)}")
    else:
        return dumper.represent_scalar("!include", data._source)

# Make literal block style the default for string output
def _represent_str(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str",
            str(data), style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

_BankLoader.add_constructor("tag:yaml.org,2002:seq", _BankList.construct)
_BankLoader.add_constructor("tag:yaml.org,2002:map", _BankDict.construct)
_BankDumper.add_representer(_BankList, _BankList.represent)
_BankDumper.add_representer(_BankDict, _BankDict.represent)

_BankLoader.add_constructor("!include", _construct_include)
_BankDumper.add_representer(_IncludedList, _represent_include)
_BankDumper.add_representer(_IncludedDict, _represent_include)

_BankDumper.add_representer(str, _represent_str)

# Register resolvers
for cls in _BankObject.__subclasses__():
    if hasattr(cls, "yaml_regex"):
        _BankLoader.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)
        _BankDumper.add_implicit_resolver(cls.yaml_tag, cls.yaml_regex, None)
    elif hasattr(cls, "zone"):
        path = ["patches", (dict, None), cls.zone, (cls.zone_type, None)]
        _BankLoader.add_path_resolver(cls.yaml_tag, path, dict)
        _BankDumper.add_path_resolver(cls.yaml_tag, path, dict)
        _BankLoader.add_path_resolver(cls.yaml_tag, path[2:], dict)
        _BankDumper.add_path_resolver(cls.yaml_tag, path[2:], dict)

