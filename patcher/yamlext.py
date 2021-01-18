"""
Copyright (c) 2020 Bill Peterson

Description: extensions to YAML classes for patcher
"""
import re, oyaml
from oyaml import safe_load, safe_load_all, safe_dump, safe_dump_all, YAMLError
          
class SFPreset(oyaml.YAMLObject):

    yaml_tag = '!sfpreset'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, name, bank, prog):
        self.name = name
        self.bank = bank
        self.prog = prog
        
    def __repr__(self):
        return '%s:%03d:%03d' % (self.name, self.bank, self.prog)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar('!sfpreset', '%s:%03d:%03d' % (data.name, data.bank, data.prog))

    @classmethod
    def from_yaml(cls, loader, node):
        vals = re.match('^(.+):(\d+):(\d+)$', loader.construct_scalar(node)).groups()
        name = vals[0]
        bank = int(vals[1])
        prog = int(vals[2])
        return SFPreset(name, bank, prog)

oyaml.add_implicit_resolver('!sfpreset', re.compile('^.+:\d+:\d+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class CCMsg(oyaml.YAMLObject):

    yaml_tag = '!ccmsg'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper

    def __init__(self, chan, cc, val):
        self.chan = chan
        self.cc = cc
        self.val = val

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar('!ccmsg', '%d/%d=%d' % (data.chan, data.cc, data.val))

    @classmethod
    def from_yaml(cls, loader, node):
        msg = re.findall('[^/=]+', loader.construct_scalar(node))
        chan, cc, val = map(int, msg)
        return CCMsg(chan, cc, val)

oyaml.add_implicit_resolver('!ccmsg', re.compile('^[0-9]+/[0-9]+=[0-9]+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

rspecex = re.compile('^([\d\.A-Gb#]+)-([\d\.A-Gb#]+)\*(-?[\d\.]+)([+-][\d\.A-Gb#]+)$')
class RouterSpec(oyaml.YAMLObject):

    yaml_tag = '!rspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add
        
    @classmethod
    def to_yaml(cls, dumper, data):
        if isinstance(data.add, int):
            rep = '%s-%s*%s%+d' % (data.min, data.max, data.mul, data.add)
        else:
            rep = '%s-%s*%s%s' % (data.min, data.max, data.mul, data.add)
        return dumper.represent_scalar('!rspec', rep)
        
    @classmethod
    def from_yaml(cls, loader, node):
        route = list(rspecex.findall(loader.construct_scalar(node))[0])
        for i, spec in enumerate(route):
            try:
                route[i] = float(spec)
            except ValueError:
                pass
            else:
                if route[i] == int(route[i]):
                    route[i] = int(route[i])
        return RouterSpec(*route)
        
oyaml.add_implicit_resolver('!rspec', rspecex,
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

class FromToSpec(oyaml.YAMLObject):

    yaml_tag = '!ftspec'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, from1, from2, to1, to2):
        self.from1 = from1
        self.from2 = from2
        self.to1 = to1
        self.to2 = to2
        
    @classmethod
    def to_yaml(cls, dumper, data):
        rep = '%d-%d=%d-%d' % (data.from1, data.from2, data.to1, data.to2)
        return dumper.represent_scalar('!ftspec', rep)

    @classmethod
    def from_yaml(cls, loader, node):
        spec = re.findall('[^-=]+', loader.construct_scalar(node))
        from1, from2, to1, to2 = map(int, spec)
        return FromToSpec(from1, from2, to1, to2)
        
oyaml.add_implicit_resolver('!ftspec', re.compile('^\d+-\d+=\d+-\d+$'),
                            Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)

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
    def to_yaml(cls, dumper, data):
        return dumper.represent_sequence('!flowseq', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return FlowSeq(loader.construct_sequence(node))

class FlowMap(oyaml.YAMLObject):

    yaml_tag = '!flowmap'
    yaml_loader = oyaml.SafeLoader
    yaml_dumper = oyaml.SafeDumper
    
    def __init__(self, **kwargs):
        for a in kwargs:
            setattr(self, a, kwargs[a])

    def __iter__(self):
        return iter(self.__dict__.items())

    def dict(self):
        return self.__dict__

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping('!flowmap', data, flow_style=True)

    @classmethod
    def from_yaml(cls, loader, node):
        return FlowMap(**loader.construct_mapping(node))

oyaml.add_path_resolver('!flowseq',
                        [(oyaml.MappingNode, 'patches'),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'cc')], 
                        kind=list, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'router_rules'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'patches'),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'router_rules'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'effects'),
                         (oyaml.SequenceNode, None),
                         (oyaml.MappingNode, 'controls'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'patches'),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'effects'),
                         (oyaml.SequenceNode, None),
                         (oyaml.MappingNode, 'controls'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'cclinks'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'cclinks'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
oyaml.add_path_resolver('!flowmap',
                        [(oyaml.MappingNode, 'patches'),
                         (oyaml.MappingNode, None),
                         (oyaml.MappingNode, 'cclinks'),
                         (oyaml.SequenceNode, None)],
                        kind=dict, Loader=oyaml.SafeLoader, Dumper=oyaml.SafeDumper)
