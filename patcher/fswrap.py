"""
Description: classes to provide an interface and some custom MIDI routing for fluidsynth via ctypes
"""
from ctypes import *
from ctypes.util import find_library
import os

def specfunc(func, restype, *argtypes):
    func.restype = restype
    func.argtypes = argtypes
    return func

if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(os.getcwd())

lib = find_library('fluidsynth') or \
    find_library('libfluidsynth-3') or \
    find_library('libfluidsynth-2') or \
    find_library('libfluidsynth')
if lib is None:
    raise ImportError("Couldn't find the FluidSynth library.")

FL = CDLL(lib)

specfunc(FL.new_fluid_settings, c_void_p)
specfunc(FL.fluid_settings_getint, c_int, c_void_p, c_char_p, POINTER(c_int))
specfunc(FL.fluid_settings_getnum, c_int, c_void_p, c_char_p, POINTER(c_double))
specfunc(FL.fluid_settings_copystr, c_int, c_void_p, c_char_p, c_char_p, c_int)
specfunc(FL.fluid_settings_setint, c_int, c_void_p, c_char_p, c_int)
specfunc(FL.fluid_settings_setnum, c_int, c_void_p, c_char_p, c_double)
specfunc(FL.fluid_settings_setstr, c_int, c_void_p, c_char_p, c_char_p)

fl_callback = CFUNCTYPE(c_void_p, c_void_p, c_void_p)
specfunc(FL.new_fluid_synth, c_void_p, c_void_p)
specfunc(FL.new_fluid_audio_driver, c_void_p, c_void_p, c_void_p)
specfunc(FL.new_fluid_midi_router, c_void_p, c_void_p, fl_callback, c_void_p)
specfunc(FL.new_fluid_midi_driver, c_void_p, c_void_p, fl_callback, c_void_p)
specfunc(FL.fluid_synth_handle_midi_event, c_int, c_void_p, c_void_p)
specfunc(FL.fluid_midi_router_handle_midi_event, c_int, c_void_p, c_void_p)

specfunc(FL.fluid_synth_sfload, c_int, c_void_p, c_char_p, c_int)
specfunc(FL.fluid_synth_sfunload, c_int, c_void_p, c_int, c_int)
specfunc(FL.fluid_synth_program_select, c_int, c_void_p, c_int, c_int, c_int, c_int)
specfunc(FL.fluid_synth_unset_program, c_int, c_void_p, c_int)
specfunc(FL.fluid_synth_get_program, c_int, c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int))
specfunc(FL.fluid_synth_cc, c_int, c_void_p, c_int, c_int, c_int)
specfunc(FL.fluid_synth_get_cc, c_int, c_void_p, c_int, c_int, POINTER(c_int))

specfunc(FL.new_fluid_midi_router_rule, c_void_p)
specfunc(FL.fluid_midi_router_rule_set_chan, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_rule_set_param1, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_rule_set_param2, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_add_rule, c_int, c_void_p, c_void_p, c_int)
specfunc(FL.fluid_midi_router_clear_rules, c_int, c_void_p)
specfunc(FL.fluid_midi_router_set_default_rules, c_int, c_void_p)

specfunc(FL.new_fluid_midi_event, c_void_p)
specfunc(FL.fluid_midi_event_get_type, c_int, c_void_p)
specfunc(FL.fluid_midi_event_get_channel, c_int, c_void_p)
fl_midi_event_get_par1 = specfunc(FL.fluid_midi_event_get_key, c_int, c_void_p)
fl_midi_event_get_par2 = specfunc(FL.fluid_midi_event_get_velocity, c_int, c_void_p)
specfunc(FL.fluid_midi_event_set_type, c_int, c_void_p, c_int)
specfunc(FL.fluid_midi_event_set_channel, c_int, c_void_p, c_int)
fl_midi_event_set_par1 = specfunc(FL.fluid_midi_event_set_key, c_int, c_void_p, c_int)
fl_midi_event_set_par2 = specfunc(FL.fluid_midi_event_set_velocity, c_int, c_void_p, c_int)

try:
    # fluidsynth 2.x
    specfunc(FL.fluid_synth_get_sfont_by_id, c_void_p, c_void_p, c_int)
    specfunc(FL.fluid_sfont_get_preset, c_void_p, c_void_p, c_int, c_int)
    specfunc(FL.fluid_preset_get_name, c_char_p, c_void_p)

    specfunc(FL.fluid_synth_get_ladspa_fx, c_void_p, c_void_p)
    specfunc(FL.fluid_ladspa_activate, c_void_p, c_void_p)
    specfunc(FL.fluid_ladspa_reset, c_int, c_void_p)
    specfunc(FL.fluid_ladspa_add_effect, c_int, c_void_p, c_char_p, c_char_p, c_char_p)
    specfunc(FL.fluid_ladspa_effect_set_mix, c_int, c_void_p, c_char_p, c_int, c_float)
    specfunc(FL.fluid_ladspa_effect_set_control, c_int, c_void_p, c_char_p, c_char_p, c_float)
    specfunc(FL.fluid_ladspa_effect_link, c_int, c_void_p, c_char_p, c_char_p, c_char_p)

    FLUID_OK = 0
    FLUID_FAILED = -1
    FLUIDSETTING_EXISTS = FLUID_OK

except:
    # fluidsynth 1.x
    class fluid_synth_channel_info_t(Structure):
        _fields_ = [
            ('assigned', c_int),
            ('sfont_id', c_int),
            ('bank', c_int),
            ('program', c_int),
            ('name', c_char*32),
            ('reserved', c_char*32)]
    specfunc(FL.fluid_synth_get_channel_info, c_int, c_void_p, c_int, POINTER(fluid_synth_channel_info_t))

    FLUID_OK = 0
    FLUID_FAILED = -1
    FLUIDSETTING_EXISTS = 1

MIDI_NOTEOFF = 0x80
MIDI_NOTEON = 0x90
MIDI_KPRESS = 0xa0
MIDI_CONTROL = 0xb0
MIDI_PROG = 0xc0
MIDI_CPRESS = 0xd0
MIDI_PBEND = 0xe0
EVENT_NAMES = 'note', 'cc', 'prog', 'pbend', 'cpress', 'kpress', 'noteoff'
MIDI_TYPES = MIDI_NOTEON, MIDI_CONTROL, MIDI_PROG, MIDI_PBEND, MIDI_CPRESS, MIDI_KPRESS, MIDI_NOTEOFF


class MidiEvent:

    def __init__(self, event):
        self.event = event

    @property
    def type(self): return FL.fluid_midi_event_get_type(self.event)        
    @type.setter
    def type(self, v): FL.fluid_midi_event_set_type(self.event, v)

    @property
    def chan(self): return FL.fluid_midi_event_get_channel(self.event)        
    @chan.setter
    def chan(self, v): FL.fluid_midi_event_set_channel(self.event, v)
    
    @property
    def par1(self): return fl_midi_event_get_par1(self.event)
    @par1.setter
    def par1(self, v): fl_midi_event_set_par1(self.event, v)

    @property
    def par2(self): return fl_midi_event_get_par2(self.event)
    @par2.setter
    def par2(self, v): fl_midi_event_set_par2(self.event, v)
        
    def __repr__(self):
        return "type: %s, chan: %d, par1: %d, par2: %d" % (self.type, self.chan, self.par1, self.par2)


class MidiMessage:

    def __init__(self, mevent):
        self.type = EVENT_NAMES[MIDI_TYPES.index(mevent.type)]
        self.chan = mevent.chan
        self.par1 = mevent.par1
        self.par2 = mevent.par2
        
    def __repr__(self):
        return str(self.__dict__)


class ExtMidiMessage(MidiMessage):

    def __init__(self, mevent, val=None, extrule=None):
        if extrule: self.__dict__.update(extrule.__dict__)
        super().__init__(mevent)
        self.val = val


class Route:

    def __init__(self, *args):
        self.min = args[0]
        self.max = args[1]
        self.mul = args[2]
        self.add = args[3]

    def __repr__(self):
        return str(self.__dict__)


class TransRule:

    def __init__(self, type, chan, par1, par2, type2):
        self.type = type
        self.chan = Route(*chan) if chan else None
        self.par1 = Route(*par1) if par1 else None
        self.par2 = Route(*par2) if par2 else None
        self.type2 = type2

    def applies(self, mevent):
        if MIDI_TYPES.index(mevent.type) != EVENT_NAMES.index(self.type):
            return False
        if self.chan:
            if self.chan.min > self.chan.max:
                if self.chan.min < mevent.chan < self.chan.max:
                    return False
            else:
                if not (self.chan.min <= mevent.chan <= self.chan.max):
                    return False
        if self.par1:
            if self.par1.min > self.par1.max:
                if self.par1.min < mevent.par1 < self.par1.max:
                    return False
            else:
                if not (self.par1.min <= mevent.par1 <= self.par1.max):
                    return False
        if self.par2:
            if self.par2.min > self.par2.max:
                if self.par2.min < mevent.par2 < self.par2.max:
                    return False
            else:
                if not (self.par2.min <= mevent.par2 <= self.par2.max):
                    return False
        return True

    def apply(self, mevent):
        newevent = MidiEvent(FL.new_fluid_midi_event())
        newevent.type = MIDI_TYPES[EVENT_NAMES.index(self.type2)]
        if self.chan:
            newevent.chan = int(mevent.chan * self.chan.mul + self.chan.add + 0.5)
        else:
            newevent.chan = mevent.chan
            
        if self.type in ('note', 'cc', 'kpress', 'noteoff'):
            if self.type2 in ('note', 'cc', 'kpress', 'noteoff'): # 2-parameter events
                if self.par1:
                    newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                else:
                    newevent.par1 = mevent.par1
                if self.par2:
                    newevent.par2 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
                else:
                    newevent.par2 = mevent.par2
            else:
                if self.par2:
                    newevent.par1 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
                else:
                    newevent.par1 = mevent.par2
        else:
            if self.type2 in ('pbend', 'prog', 'cpress'): # 1-parameter events
                if self.par1:
                    newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                else:
                    newevent.par1 = mevent.par1
            else:
                if self.par1:
                    newevent.par2 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                else:
                    newevent.par2 = mevent.par1
                if self.par2:
                    newevent.par1 = self.par2.min
                else: newevent.par1 = 1
        return newevent


class ExtRule(TransRule):

    def __init__(self, type, chan, par1, par2, **kwargs):
        self.type = type
        self.chan = Route(*chan) if chan else None
        self.par1 = Route(*par1) if par1 else None
        self.par2 = Route(*par2) if par2 else None
        for attr, val in kwargs.items():
            setattr(self, attr, val)

    def apply(self, msg):
        if self.type in ('note', 'cc', 'kpress'):
            if self.par2:
                val = msg.par2 * self.par2.mul + self.par2.add
            else:
                val = msg.par2
        else:
            if self.par1:
                val = msg.par1 * self.par1.mul + self.par1.add
            else:
                val = msg.par1
        return ExtMidiMessage(msg, val, self)


class Synth:

    def __init__(self, **settings):
        self.st = FL.new_fluid_settings()
        for opt, val in settings.items():
            self.setting(opt, val)

        self.synth = FL.new_fluid_synth(self.st)
        FL.new_fluid_audio_driver(self.st, self.synth)
        self.fx = FL.fluid_synth_get_ladspa_fx(self.synth)
        self.synth_eventhandle = fl_callback(FL.fluid_synth_handle_midi_event)
        self.router = FL.new_fluid_midi_router(self.st, self.synth_eventhandle, self.synth)
        self.driver_eventhandle = fl_callback(self.custom_midi_router)
        FL.new_fluid_midi_driver(self.st, self.driver_eventhandle, self.router)

        self.sfid = {}
        self.xrules = []
        self.callback = None

    def custom_midi_router(self, router, event):
        mevent = MidiEvent(event)
        for rule in self.xrules:
            if rule.applies(mevent):
                res = rule.apply(mevent)
                if isinstance(res, MidiEvent):
                    self.synth_eventhandle(self.synth, res.event)
                else:
                    if hasattr(res, 'fluidsetting'):
                        self.setting(res.fluidsetting, res.val)
                    elif hasattr(res, 'ladspafx'):
                        self.fx_setcontrol(res.ladspafx, res.port, res.val)
                    elif hasattr(res, 'ladspafxmix'):
                        self.fx_setmix(res.ladspafxmix, res.val)
                    else:
                        if self.callback != None:
                            self.callback(res)
        if self.callback != None:
            self.callback(MidiMessage(mevent))
        return FL.fluid_midi_router_handle_midi_event(router, event)

    def setting(self, opt, val):
        if isinstance(val, str):
            FL.fluid_settings_setstr(self.st, opt.encode(), val.encode())
        elif isinstance(val, int):
            FL.fluid_settings_setint(self.st, opt.encode(), val)
        elif isinstance(val, float):
            FL.fluid_settings_setnum(self.st, opt.encode(), c_double(val))

    def get_setting(self, opt):
        val = c_int()
        if FL.fluid_settings_getint(self.st, opt.encode(), byref(val)) == FLUIDSETTING_EXISTS:
            return val.value
        strval = create_string_buffer(32)
        if FL.fluid_settings_copystr(self.st, opt.encode(), strval, 32) == FLUIDSETTING_EXISTS:
            return strval.value.decode()
        num = c_double()
        if FL.fluid_settings_getnum(self.st, opt.encode(), byref(num)) == FLUIDSETTING_EXISTS:
            return round(num.value, 6)
        return None

    def load_soundfont(self, sfont):
        id = FL.fluid_synth_sfload(self.synth, sfont.encode(), False)
        if id == FLUID_FAILED:
            return False
        self.sfid[sfont] = id
        return True

    def unload_soundfont(self, sfont):
        if FL.fluid_synth_sfunload(self.synth, self.sfid[sfont], False) == FLUID_FAILED:
            return False
        del self.sfid[sfont]
        return True

    def program_select(self, chan, sfont, bank, prog):
        if sfont not in self.sfid:
            return False
        x = FL.fluid_synth_program_select(self.synth, chan, self.sfid[sfont], bank, prog)
        if x == FLUID_FAILED:
            return False
        return True

    def program_unset(self, chan):
        FL.fluid_synth_unset_program(self.synth, chan)

    def program_info(self, chan):
        id = c_int()
        bank = c_int()
        prog = c_int()
        FL.fluid_synth_get_program(self.synth, chan, byref(id), byref(bank), byref(prog))
        if id.value not in self.sfid.values():
            return None
        sfont = {v: k for k, v in self.sfid.items()}[id.value]
        return sfont, bank.value, prog.value

    def send_cc(self, chan, ctrl, val):
        FL.fluid_synth_cc(self.synth, chan, ctrl, val)

    def get_cc(self, chan, ctrl):
        val = c_int()
        FL.fluid_synth_get_cc(self.synth, chan, ctrl, byref(val))
        return val.value

    def router_clear(self):
        FL.fluid_midi_router_clear_rules(self.router)
        self.xrules = []

    def router_default(self):
        FL.fluid_midi_router_set_default_rules(self.router)
        self.xrules = []

    def router_addrule(self, type, chan, par1, par2, **kwargs):
        if 'type2' in kwargs:
            self.xrules.append(TransRule(type, chan, par1, par2, kwargs['type2']))
        elif kwargs:
            self.xrules.append(ExtRule(type, chan, par1, par2, **kwargs))
        else:
            rule = FL.new_fluid_midi_router_rule()
            ntype = EVENT_NAMES.index(type)
            if chan:
                FL.fluid_midi_router_rule_set_chan(rule, *chan)
            if par1:
                FL.fluid_midi_router_rule_set_param1(rule, *par1)
            if par2:
                FL.fluid_midi_router_rule_set_param2(rule, *par2)
            FL.fluid_midi_router_add_rule(self.router, rule, ntype)

    try:
        # fluidsynth 2.x
        def get_preset_name(self, sfont, bank, prog):
            sfont_obj = FL.fluid_synth_get_sfont_by_id(self.synth, self.sfid[sfont])
            preset_obj = FL.fluid_sfont_get_preset(sfont_obj, bank, prog)
            if not preset_obj:
                return None
            return FL.fluid_preset_get_name(preset_obj).decode()

        def fxchain_clear(self):
            FL.fluid_ladspa_reset(self.fx)

        def fxchain_add(self, name, lib, plugin):
            if plugin != None:
                plugin = plugin.encode()
            if FL.fluid_ladspa_add_effect(self.fx, name.encode(), lib.encode(), plugin) == FLUID_FAILED:
                return False
            return True

        def fxchain_link(self, name, fromport, toport):
            if FL.fluid_ladspa_effect_link(self.fx, name.encode(), fromport.encode(), toport.encode()) == FLUID_FAILED:
                return False
            return True

        def fxchain_activate(self):
            FL.fluid_ladspa_activate(self.fx)

        def fx_setcontrol(self, name, port, val):
            for name in [name + s for s in ('L', 'R', '')]:
                FL.fluid_ladspa_effect_set_control(self.fx, name.encode(), port.encode(), c_float(val))

        def fx_setmix(self, name, gain):
            FL.fluid_ladspa_effect_set_mix(self.fx, name.encode(), 1, c_float(gain))

    except:
        # fluidsynth 1.x
        def get_preset_name(self, sfont, bank, prog):
            if not self.program_select(0, sfont, bank, prog):
                return None
            info = fluid_synth_channel_info_t()
            FL.fluid_synth_get_channel_info(self.synth, 0, byref(info))
            return info.name.decode()

        def fxchain_clear(self):
            pass

        def fxchain_add(self, name, lib, plugin):
            return True

        def fxchain_link(self, name, fromport, toport):
            pass

        def fxchain_activate(self):
            pass

        def fx_setcontrol(self, name, port, val):
            pass

        def fx_setmix(self, name, gain):
            pass
