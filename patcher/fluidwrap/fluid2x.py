"""
Description: ctypes bindings for fluidsynth 2.x
"""
from ctypes import *
from ctypes.util import find_library
import os

if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(os.getcwd())

lib = find_library('fluidsynth') or \
    find_library('libfluidsynth-3') or \
    find_library('libfluidsynth-2') or \
    find_library('libfluidsynth')
if lib is None:
    raise ImportError("Couldn't find the FluidSynth library.")

FL = CDLL(lib)

FL.new_fluid_settings.argtypes = []
FL.new_fluid_settings.restype = c_void_p

FL.new_fluid_synth.argtypes = [c_void_p]
FL.new_fluid_synth.restype = c_void_p

FL.new_fluid_audio_driver.argtypes = [c_void_p, c_void_p]
FL.new_fluid_audio_driver.restype = c_void_p

fl_callback = CFUNCTYPE(c_void_p, c_void_p, c_void_p)
FL.new_fluid_midi_router.argtypes = [c_void_p, fl_callback, c_void_p]
FL.new_fluid_midi_router.restype = c_void_p

FL.new_fluid_midi_driver.argtypes = [c_void_p, fl_callback, c_void_p]
FL.new_fluid_midi_driver.restype = c_void_p

FL.new_fluid_midi_router_rule.argtypes = []
FL.new_fluid_midi_router_rule.restype = c_void_p

FL.fluid_settings_setint.argtypes = [c_void_p, c_char_p, c_int]
FL.fluid_settings_setint.restype = c_int
FL.fluid_settings_setnum.argtypes = [c_void_p, c_char_p, c_double]
FL.fluid_settings_setnum.restype = c_int
FL.fluid_settings_setstr.argtypes = [c_void_p, c_char_p, c_char_p]
FL.fluid_settings_setstr.restype = c_int
FL.fluid_settings_getint.argtypes = [c_void_p, c_char_p, POINTER(c_int)]
FL.fluid_settings_getint.restype = c_int
FL.fluid_settings_getnum.argtypes = [c_void_p, c_char_p, POINTER(c_double)]
FL.fluid_settings_getnum.restype = c_int
FL.fluid_settings_copystr.argtypes = [c_void_p, c_char_p, c_char_p, c_int]
FL.fluid_settings_copystr.restype = c_int

FL.fluid_synth_handle_midi_event.argtypes = [c_void_p, c_void_p]
FL.fluid_synth_handle_midi_event.restype = c_int
FL.fluid_synth_sfload.argtypes = [c_void_p, c_char_p, c_int]
FL.fluid_synth_sfload.restype = c_int
FL.fluid_synth_sfunload.argtypes = [c_void_p, c_int, c_int]
FL.fluid_synth_sfunload.restype = c_int
FL.fluid_synth_program_select.argtypes = [c_void_p, c_int, c_int, c_int, c_int]
FL.fluid_synth_program_select.restype = c_int
FL.fluid_synth_unset_program.argtypes = [c_void_p, c_int]
FL.fluid_synth_unset_program.restype = c_int
FL.fluid_synth_get_program.argtypes = [c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int)]
FL.fluid_synth_get_program.restype = c_int
FL.fluid_synth_cc.argtypes = [c_void_p, c_int, c_int, c_int]
FL.fluid_synth_cc.restype = c_int
FL.fluid_synth_get_cc.argtypes = [c_void_p, c_int, c_int, POINTER(c_int)]
FL.fluid_synth_get_cc.restype = c_int
FL.fluid_synth_noteon.argtypes = [c_void_p, c_int, c_int, c_int]
FL.fluid_synth_noteon.restype = c_int
FL.fluid_synth_noteoff.argtypes = [c_void_p, c_int, c_int]
FL.fluid_synth_noteoff.restype = c_int

FL.fluid_midi_router_handle_midi_event.argtypes = [c_void_p, c_void_p]
FL.fluid_midi_router_handle_midi_event.restype = c_int
FL.fluid_midi_router_clear_rules.argtypes = [c_void_p]
FL.fluid_midi_router_clear_rules.restype = c_int
FL.fluid_midi_router_set_default_rules.argtypes = [c_void_p]
FL.fluid_midi_router_set_default_rules.restype = c_int
FL.fluid_midi_router_rule_set_chan.argtypes = [c_void_p, c_int, c_int, c_float, c_int]
FL.fluid_midi_router_rule_set_chan.restype = None
FL.fluid_midi_router_rule_set_param1.argtypes = [c_void_p, c_int, c_int, c_float, c_int]
FL.fluid_midi_router_rule_set_param1.restype = None
FL.fluid_midi_router_rule_set_param2.argtypes = [c_void_p, c_int, c_int, c_float, c_int]
FL.fluid_midi_router_rule_set_param2.restype = None
FL.fluid_midi_router_add_rule.argtypes = [c_void_p, c_void_p, c_int]
FL.fluid_midi_router_add_rule.restype = c_int

# fluidsynth 2.x
FL.fluid_synth_get_sfont_by_id.argtypes = [c_void_p, c_int]
FL.fluid_synth_get_sfont_by_id.restype = c_void_p
FL.fluid_sfont_get_preset.argtypes = [c_void_p, c_int, c_int]
FL.fluid_sfont_get_preset.restype = c_void_p
FL.fluid_preset_get_name.argtypes = [c_void_p]
FL.fluid_preset_get_name.restype = c_char_p

FL.fluid_synth_get_ladspa_fx.argtypes = [c_void_p]
FL.fluid_synth_get_ladspa_fx.restype = c_void_p
FL.fluid_ladspa_activate.argtypes = [c_void_p]
FL.fluid_ladspa_activate.restype = c_void_p
FL.fluid_ladspa_reset.argtypes = [c_void_p]
FL.fluid_ladspa_reset.restype = c_int
FL.fluid_ladspa_effect_set_control.argtypes = [c_void_p, c_char_p, c_char_p, c_float]
FL.fluid_ladspa_effect_set_control.restype = c_int
FL.fluid_ladspa_add_effect.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p]
FL.fluid_ladspa_add_effect.restype = c_int
FL.fluid_ladspa_effect_link.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p]
FL.fluid_ladspa_effect_link.restype = c_int

FLUID_OK = 0
FLUID_FAILED = -1
FLUIDSETTING_EXISTS = FLUID_OK

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
        self.driver_eventhandle = fl_callback(FL.fluid_midi_router_handle_midi_event)
        FL.new_fluid_midi_driver(self.st, self.driver_eventhandle, self.router)

        self.sfid = {}

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

    def get_preset_name(self, sfont, bank, prog):
        sfont_obj = FL.fluid_synth_get_sfont_by_id(self.synth, self.sfid[sfont])
        preset_obj = FL.fluid_sfont_get_preset(sfont_obj, bank, prog)
        if not preset_obj:
            return None
        return FL.fluid_preset_get_name(preset_obj).decode('ascii')

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

    def noteon(self, chan, key, vel):
        FL.fluid_synth_noteon(self.synth, chan, key, vel)

    def noteoff(self, chan, key):
        FL.fluid_synth_noteoff(self.synth, chan, key)

    def send_cc(self, chan, ctrl, val):
        FL.fluid_synth_cc(self.synth, chan, ctrl, val)

    def get_cc(self, chan, num):
        i=c_int()
        FL.fluid_synth_get_cc(self.synth, chan, num, byref(i))
        return i.value

    def router_clear(self):
        FL.fluid_midi_router_clear_rules(self.router)

    def router_default(self):
        FL.fluid_midi_router_set_default_rules(self.router)

    def router_addrule(self, type, chan, par1, par2):
        rule = FL.new_fluid_midi_router_rule()
        ntype = ['note', 'cc', 'prog', 'pbend', 'cpress', 'kpress'].index(type)
        if chan:
            FL.fluid_midi_router_rule_set_chan(rule, *chan)
        if par1:
            FL.fluid_midi_router_rule_set_param1(rule, *par1)
        if par2:
            FL.fluid_midi_router_rule_set_param2(rule, *par2)
        FL.fluid_midi_router_add_rule(self.router, rule, ntype)

    def fxchain_clear(self):
        FL.fluid_ladspa_reset(self.fx)
        
    def fxchain_add(self, label, lib, plugin):
        if plugin != None:
            plugin = plugin.encode()
        if FL.fluid_ladspa_add_effect(self.fx, label.encode(), lib.encode(), plugin) == FLUID_FAILED:
            return False
        return True

    def fxchain_link(self, label, fromport, toport):
        if FL.fluid_ladspa_effect_link(self.fx, label.encode(), fromport.encode(), toport.encode()) == FLUID_FAILED:
            return False
        return True
        
    def fxchain_activate(self):
        retval = FL.fluid_ladspa_activate(self.fx)
        
    def fx_setcontrol(self, label, port, val):
        FL.fluid_ladspa_effect_set_control(self.fx, label.encode(), port.encode(), c_float(val))
        