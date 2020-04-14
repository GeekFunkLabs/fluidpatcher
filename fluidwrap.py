from ctypes import *
from ctypes.util import find_library

lib = find_library('fluidsynth') or \
    find_library('libfluidsynth') or \
    find_library('libfluidsynth-1')
if lib is None:
    raise ImportError("Couldn't find the FluidSynth library.")
FL = CDLL(lib)

# handle FluidSynth 1.x/2.x differences
if hasattr(FL, 'fluid_preset_get_name'):
    FL.fluid_preset_get_name.restype = c_char_p
else:
    class fluid_synth_channel_info_t(Structure):
        _fields_ = [
            ('assigned', c_int),
            ('sfont_id', c_int),
            ('bank', c_int),
            ('program', c_int),
            ('name', c_char*32),
            ('reserved', c_char*32)]

class fluid_midi_router_t(Structure):
    _fields_ = [
        ('synth', c_void_p),
        ('rules_mutex', c_void_p),
        ('rules', c_void_p*6),
        ('free_rules', c_void_p),
        ('event_handler', c_void_p),
        ('event_handler_data', c_void_p),
        ('nr_midi_channels', c_int),
        ('cmd_rule', c_void_p),
        ('cmd_rule_type', POINTER(c_int))]

FL.new_fluid_midi_router.restype = POINTER(fluid_midi_router_t)

FLUID_OK = 0
FLUID_FAILED = -1
FLUID_CHORUS_MOD_SINE = 0

class Synth:

    def __init__(self, **settings):
        self.st = FL.new_fluid_settings()
        for opt, val in settings.items():
            self.setting(opt, val)
        self.synth = FL.new_fluid_synth(self.st)
        FL.new_fluid_audio_driver(self.st, self.synth)

        self.router = FL.new_fluid_midi_router(self.st, FL.fluid_synth_handle_midi_event, self.synth)
        FL.new_fluid_cmd_handler(self.synth, self.router)
        FL.new_fluid_midi_driver(self.st, FL.fluid_midi_router_handle_midi_event, self.router)

        self.sfid = {}

    def setting(self, opt, val):
        if isinstance(val, str):
            FL.fluid_settings_setstr(self.st, opt.encode(), val.encode())
        elif isinstance(val, int):
            FL.fluid_settings_setint(self.st, opt.encode(), val)
        elif isinstance(val, float):
            FL.fluid_settings_setnum(self.st, opt.encode(), c_double(val))

    def get_setting(self, opt):
        num = c_double()
        if FL.fluid_settings_getnum(self.st, opt.encode(), byref(num)) != FLUID_FAILED:
            return round(num.value, 6)
        val = c_int()
        if FL.fluid_settings_getint(self.st, opt.encode(), byref(val)) != FLUID_FAILED:
            return val.value
        strval = create_string_buffer(32)
        if FL.fluid_settings_copystr(self.st, opt.encode(), byref(strval), 32) != FLUID_FAILED:
            return strval.decode('ascii')
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
        if hasattr(FL, 'fluid_sfont_get_preset'):
            sfont_obj = FL.fluid_synth_get_sfont_by_id(self.synth, self.sfid[sfont])
            preset_obj = FL.fluid_sfont_get_preset(sfont_obj, bank, prog)
            if not preset_obj:
                return None
            return FL.fluid_preset_get_name(preset_obj).decode('ascii')
        else:
            if not self.program_select(0, sfont, bank, prog):
                return None
            info = fluid_synth_channel_info_t()
            FL.fluid_synth_get_channel_info(self.synth, 0, byref(info))
            return info.name.decode('ascii')

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

    def router_clear(self):
        FL.fluid_midi_router_clear_rules(self.router)

    def router_default(self):
        FL.fluid_midi_router_set_default_rules(self.router)

    def router_addrule(self, type, chan, par1, par2):
        self.router.cmd_rule = FL.new_fluid_midi_router_rule()
        ruletypes = ['note', 'cc', 'prog', 'pbend', 'cpress', 'kpress']
        self.router.cmd_rule_type = ruletypes.index(type)
        if chan:
            FL.fluid_midi_router_rule_set_chan(
                self.router.cmd_rule, chan[0], chan[1], c_float(chan[2]), chan[3]
            )
        if par1:
            FL.fluid_midi_router_rule_set_param1(
                self.router.cmd_rule, par1[0], par1[1], c_float(par1[2]), par1[3]
            )
        if par2:
            FL.fluid_midi_router_rule_set_param2(
                self.router.cmd_rule, par2[0], par2[1], c_float(par2[2]), par2[3]
            )
        FL.fluid_midi_router_add_rule(self.router, self.router.cmd_rule, self.router.cmd_rule_type)

    def send_cc(self, chan, ctrl, val):
        FL.fluid_synth_cc(self.synth, chan, ctrl, val)

    def get_cc(self, chan, num):
        i=c_int()
        FL.fluid_synth_get_cc(self.synth, chan, num, byref(i))
        return i.value

    def noteon(self, chan, key, vel):
        FL.fluid_synth_noteon(self.synth, chan, key, vel)

    def noteoff(self, chan, key):
        FL.fluid_synth_noteoff(self.synth, chan, key)
