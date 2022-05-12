"""
Description: classes to provide an interface and some custom MIDI routing for fluidsynth via ctypes
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
def specfunc(func, restype, *argtypes):
    func.restype = restype
    func.argtypes = argtypes
    return func

major, minor, micro = c_int(), c_int(), c_int()
specfunc(FL.fluid_version, c_void_p, POINTER(c_int), POINTER(c_int), POINTER(c_int))(major, minor, micro)
FLUID_VERSION = major.value, minor.value, micro.value
FLUID_OK = 0
FLUID_FAILED = -1

# settings
specfunc(FL.new_fluid_settings, c_void_p)
specfunc(FL.fluid_settings_getint, c_int, c_void_p, c_char_p, POINTER(c_int))
specfunc(FL.fluid_settings_getnum, c_int, c_void_p, c_char_p, POINTER(c_double))
specfunc(FL.fluid_settings_copystr, c_int, c_void_p, c_char_p, c_char_p, c_int)
specfunc(FL.fluid_settings_setint, c_int, c_void_p, c_char_p, c_int)
specfunc(FL.fluid_settings_setnum, c_int, c_void_p, c_char_p, c_double)
specfunc(FL.fluid_settings_setstr, c_int, c_void_p, c_char_p, c_char_p)

# synth
fl_eventcallback = CFUNCTYPE(c_int, c_void_p, c_void_p)
specfunc(FL.new_fluid_synth, c_void_p, c_void_p)
specfunc(FL.fluid_synth_system_reset, c_int, c_void_p)
specfunc(FL.new_fluid_audio_driver, c_void_p, c_void_p, c_void_p)
specfunc(FL.new_fluid_midi_router, c_void_p, c_void_p, fl_eventcallback, c_void_p)
specfunc(FL.new_fluid_midi_driver, c_void_p, c_void_p, fl_eventcallback, c_void_p)
specfunc(FL.fluid_synth_handle_midi_event, c_int, c_void_p, c_void_p)
specfunc(FL.fluid_midi_router_handle_midi_event, c_int, c_void_p, c_void_p)
specfunc(FL.fluid_synth_sfload, c_int, c_void_p, c_char_p, c_int)
specfunc(FL.fluid_synth_sfunload, c_int, c_void_p, c_int, c_int)
specfunc(FL.fluid_synth_program_select, c_int, c_void_p, c_int, c_int, c_int, c_int)
specfunc(FL.fluid_synth_unset_program, c_int, c_void_p, c_int)
specfunc(FL.fluid_synth_get_program, c_int, c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int))
specfunc(FL.fluid_synth_cc, c_int, c_void_p, c_int, c_int, c_int)
specfunc(FL.fluid_synth_get_cc, c_int, c_void_p, c_int, c_int, POINTER(c_int))

# router rules
specfunc(FL.new_fluid_midi_router_rule, c_void_p)
specfunc(FL.fluid_midi_router_rule_set_chan, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_rule_set_param1, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_rule_set_param2, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FL.fluid_midi_router_add_rule, c_int, c_void_p, c_void_p, c_int)
specfunc(FL.fluid_midi_router_clear_rules, c_int, c_void_p)
specfunc(FL.fluid_midi_router_set_default_rules, c_int, c_void_p)

# midi events
specfunc(FL.new_fluid_midi_event, c_void_p)
specfunc(FL.delete_fluid_event, None, c_void_p)
specfunc(FL.fluid_midi_event_get_type, c_int, c_void_p)
specfunc(FL.fluid_midi_event_get_channel, c_int, c_void_p)
fl_midi_event_get_par1 = specfunc(FL.fluid_midi_event_get_key, c_int, c_void_p)
fl_midi_event_get_par2 = specfunc(FL.fluid_midi_event_get_velocity, c_int, c_void_p)
specfunc(FL.fluid_midi_event_set_type, c_int, c_void_p, c_int)
specfunc(FL.fluid_midi_event_set_channel, c_int, c_void_p, c_int)
fl_midi_event_set_par1 = specfunc(FL.fluid_midi_event_set_key, c_int, c_void_p, c_int)
fl_midi_event_set_par2 = specfunc(FL.fluid_midi_event_set_velocity, c_int, c_void_p, c_int)
specfunc(FL.fluid_midi_event_set_sysex, c_int, c_void_p, c_void_p, c_int, c_int)

# sequencer events
specfunc(FL.new_fluid_event, c_void_p)
specfunc(FL.delete_fluid_event, None, c_void_p)
specfunc(FL.fluid_event_noteon, None, c_void_p, c_int, c_int, c_int)
specfunc(FL.fluid_event_noteoff, None, c_void_p, c_int, c_int)
specfunc(FL.fluid_event_set_source, None, c_void_p, c_void_p)
specfunc(FL.fluid_event_set_dest, None, c_void_p, c_void_p)
specfunc(FL.fluid_event_timer, None, c_void_p, c_void_p)
specfunc(FL.fluid_event_get_type, c_int, c_void_p)

# sequencer
fl_seqcallback = CFUNCTYPE(None, c_uint, c_void_p, c_void_p, c_void_p)
specfunc(FL.new_fluid_sequencer2, c_void_p, c_int)
specfunc(FL.delete_fluid_sequencer, None, c_void_p)
specfunc(FL.fluid_sequencer_register_fluidsynth, c_short, c_void_p, c_void_p)
specfunc(FL.fluid_sequencer_register_client, c_short, c_void_p, c_char_p, fl_seqcallback, c_void_p)
specfunc(FL.fluid_sequencer_unregister_client, None, c_void_p, c_short)
specfunc(FL.fluid_sequencer_set_time_scale, None, c_void_p, c_double)
specfunc(FL.fluid_sequencer_send_at, c_int, c_void_p, c_void_p, c_uint, c_int)
specfunc(FL.fluid_sequencer_remove_events, None, c_void_p, c_short, c_short, c_int)
specfunc(FL.fluid_sequencer_get_tick, c_uint, c_void_p)
FLUID_SEQ_NOTEON = 1
FLUID_SEQ_TIMER = 17
FLUID_SEQ_UNREGISTERING = 21

# player
fl_tickcallback = CFUNCTYPE(None, c_void_p, c_uint)
specfunc(FL.new_fluid_player, c_void_p, c_void_p)
specfunc(FL.delete_fluid_player, None, c_void_p)
specfunc(FL.fluid_player_add, c_int, c_void_p, c_char_p)
specfunc(FL.fluid_player_set_playback_callback, c_int, c_void_p, fl_eventcallback, c_void_p)
specfunc(FL.fluid_player_play, c_int, c_void_p)
specfunc(FL.fluid_player_stop, c_int, c_void_p)
specfunc(FL.fluid_player_get_status, c_int, c_void_p)
specfunc(FL.fluid_player_get_total_ticks, c_int, c_void_p)
FLUID_PLAYER_TEMPO_INTERNAL = 0
FLUID_PLAYER_TEMPO_EXTERNAL_MIDI = 2
FLUID_PLAYER_PLAYING = 1
FLUID_PLAYER_DONE = 3

if FLUID_VERSION >= (2, 2, 0):
    specfunc(FL.fluid_player_set_tick_callback, c_int, c_void_p, fl_tickcallback, c_void_p)
    specfunc(FL.fluid_player_set_tempo, c_int, c_void_p, c_int, c_double)
if FLUID_VERSION >= (2, 0, 0):
    specfunc(FL.fluid_synth_get_sfont_by_id, c_void_p, c_void_p, c_int)
    specfunc(FL.fluid_sfont_iteration_start, None, c_void_p)
    specfunc(FL.fluid_sfont_iteration_next, c_void_p, c_void_p)
    specfunc(FL.fluid_preset_get_name, c_char_p, c_void_p)
    specfunc(FL.fluid_preset_get_banknum, c_int, c_void_p)
    specfunc(FL.fluid_preset_get_num, c_int, c_void_p)
    specfunc(FL.fluid_player_seek, c_int, c_void_p, c_int)
    specfunc(FL.fluid_synth_get_ladspa_fx, c_void_p, c_void_p)
    FLUIDSETTING_EXISTS = FLUID_OK
else:
    class fluid_synth_channel_info_t(Structure):
        _fields_ = [
            ('assigned', c_int),
            ('sfont_id', c_int),
            ('bank', c_int),
            ('program', c_int),
            ('name', c_char*32),
            ('reserved', c_char*32)]
    specfunc(FL.fluid_synth_get_channel_info, c_int, c_void_p, c_int, POINTER(fluid_synth_channel_info_t))
    FLUIDSETTING_EXISTS = 1

try:
    specfunc(FL.fluid_ladspa_activate, c_void_p, c_void_p)
    specfunc(FL.fluid_ladspa_is_active, c_int, c_void_p)
    specfunc(FL.fluid_ladspa_reset, c_int, c_void_p)
    specfunc(FL.fluid_ladspa_add_effect, c_int, c_void_p, c_char_p, c_char_p, c_char_p)
    specfunc(FL.fluid_ladspa_add_buffer, c_int, c_void_p, c_char_p)
    specfunc(FL.fluid_ladspa_buffer_exists, c_int, c_void_p, c_char_p)
    specfunc(FL.fluid_ladspa_effect_set_control, c_int, c_void_p, c_char_p, c_char_p, c_float)
    specfunc(FL.fluid_ladspa_effect_link, c_int, c_void_p, c_char_p, c_char_p, c_char_p)
    LADSPA_SUPPORT = True
except AttributeError:
    LADSPA_SUPPORT = False

MIDI_NOTEOFF = 0x80
MIDI_NOTEON = 0x90
MIDI_KPRESS = 0xa0
MIDI_CONTROL = 0xb0
MIDI_PROG = 0xc0
MIDI_CPRESS = 0xd0
MIDI_PBEND = 0xe0
EVENT_NAMES = 'note', 'cc', 'prog', 'pbend', 'cpress', 'kpress', 'noteoff'
MIDI_TYPES = MIDI_NOTEON, MIDI_CONTROL, MIDI_PROG, MIDI_PBEND, MIDI_CPRESS, MIDI_KPRESS, MIDI_NOTEOFF
SEEK_DONE = -1
SEEK_WAIT = -2


class MidiEvent:

    def __init__(self, event):
        self.event = event

    @property
    def type(self):
        b = FL.fluid_midi_event_get_type(self.event)
        return b if b in MIDI_TYPES else None
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
        if mevent.type in MIDI_TYPES:
            self.type = EVENT_NAMES[MIDI_TYPES.index(mevent.type)]
        else:
            self.type = None
        self.chan = mevent.chan
        self.par1 = mevent.par1
        self.par2 = mevent.par2
        
    def __repr__(self):
        return str(self.__dict__)


class ExtMidiMessage(MidiMessage):

    def __init__(self, mevent, extrule=None, val=None):
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

    def __repr__(self):
        return str(self.__dict__)

    def applies(self, mevent):
        if MIDI_TYPES.index(mevent.type) != EVENT_NAMES.index(self.type):
            return False
        if self.chan != None:
            if self.chan.min > self.chan.max:
                if self.chan.min < mevent.chan < self.chan.max:
                    return False
            else:
                if not (self.chan.min <= mevent.chan <= self.chan.max):
                    return False
        if self.par1 != None:
            if self.par1.min > self.par1.max:
                if self.par1.min < mevent.par1 < self.par1.max:
                    return False
            else:
                if not (self.par1.min <= mevent.par1 <= self.par1.max):
                    return False
        if self.type in ('note', 'cc', 'kpress', 'noteoff') and self.par2 != None:
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
        if self.chan == None:
            newevent.chan = mevent.chan
        else:
            newevent.chan = int(mevent.chan * self.chan.mul + self.chan.add + 0.5)
        if self.type in ('note', 'cc', 'kpress', 'noteoff'): # 2-parameter events
            if self.type2 in ('note', 'cc', 'kpress', 'noteoff'): # 2-parameter targets
                if self.par1 == None:
                    newevent.par1 = mevent.par1
                else:
                    newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                if self.par2 == None:
                    newevent.par2 = mevent.par2
                else:
                    newevent.par2 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
            else: # 1-parameter targets
                if self.par2 == None:
                    newevent.par1 = mevent.par2
                else:
                    newevent.par1 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
        else: # 1-parameter events
            if self.type2 in ('pbend', 'prog', 'cpress'): # 1-parameter targets
                if self.par1 == None:
                    newevent.par1 = mevent.par1
                else:
                    newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
            else: # 2-parameter targets
                if self.par1 == None:
                    newevent.par2 = mevent.par1
                else:
                    newevent.par2 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                if self.par2:
                    newevent.par1 = self.par2.min
                else: newevent.par1 = 1
        return newevent


class ExtRule(TransRule):

    def __init__(self, type, chan, par1, par2, **apars):
        self.type = type
        self.chan = Route(*chan) if chan else None
        self.par1 = Route(*par1) if par1 else None
        self.par2 = Route(*par2) if par2 else None
        for attr, val in apars.items():
            setattr(self, attr, val)

    def apply(self, mevent):
        msg = ExtMidiMessage(mevent, extrule=self)
        if self.chan != None:
            msg.chan = int(mevent.chan * self.chan.mul + self.chan.add + 0.5)
        if self.par1 != None:
            msg.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
        if self.par2 != None:
            msg.par2 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
        if self.type in ('note', 'cc', 'kpress', 'noteoff'):
            msg.val = mevent.par2
            if self.par2: msg.val = msg.val * self.par2.mul + self.par2.add
        else:
            msg.val = mevent.par1
            if self.par1: msg.val = msg.val * self.par1.mul + self.par1.add
        return msg


class PresetInfo:
    
    if FLUID_VERSION >= (2, 0, 0):
        def __init__(self, preset_obj):        
            self.name = FL.fluid_preset_get_name(preset_obj).decode()
            self.bank = FL.fluid_preset_get_banknum(preset_obj)
            self.prog = FL.fluid_preset_get_num(preset_obj)
    else:
        def __init__(self, name, bank, prog):        
            self.name = name
            self.bank = bank
            self.prog = prog


class SequencerNote:

    def __init__(self, chan, key, vel):
        self.chan = chan
        self.key = key
        self.vel = vel

    def schedule(self, seq, timeon, timeoff):
        evt = FL.new_fluid_event()
        FL.fluid_event_set_source(evt, -1)
        FL.fluid_event_set_dest(evt, seq.fsynth_dest)
        FL.fluid_event_noteon(evt, int(self.chan), int(self.key), int(self.vel))
        FL.fluid_sequencer_send_at(seq.fseq, evt, int(timeon), 1)
        FL.delete_fluid_event(evt)
        evt = FL.new_fluid_event()
        FL.fluid_event_set_source(evt, -1)
        FL.fluid_event_set_dest(evt, seq.fsynth_dest)
        FL.fluid_event_noteoff(evt, int(self.chan), int(self.key))
        FL.fluid_sequencer_send_at(seq.fseq, evt, int(timeoff), 1)
        FL.delete_fluid_event(evt)


class Sequencer:

    def __init__(self, synth, notes, tdiv, swing):
        self.fseq = FL.new_fluid_sequencer2(0)
        self.fsynth_dest = FL.fluid_sequencer_register_fluidsynth(self.fseq, synth.fsynth)
        self.callback = fl_seqcallback(self.scheduler)
        self.fseq_dest = FL.fluid_sequencer_register_client(self.fseq, b'seq', self.callback, None)
        self.notes = [SequencerNote(chan, key, vel) for _, chan, key, vel in notes]
        self.tdiv = tdiv
        self.swing = swing
        self.ticksperbeat = 500 # default 120bpm at 1000 ticks/sec

    def scheduler(self, time=None, event=None, fseq=None, data=None):
        if event and FL.fluid_event_get_type(event) == FLUID_SEQ_UNREGISTERING:
            return
        if not self.notes: return
        dur = self.ticksperbeat * 4 / self.tdiv
        if self.tdiv >= 8 and self.tdiv % 3:
            if self.beat % 2: dur *= 2 * (1 - self.swing)
            else: dur *= 2 * self.swing
        pos = self.beat % len(self.notes)
        self.notes[pos].schedule(self, self.nextnote, self.nextnote + dur)
        if pos == len(self.notes) - 1:
            self.loop -= 1
        if self.loop != 0:
            self.timer(self.nextnote + 0.5 * dur)
            self.nextnote += dur
            self.beat += 1

    def play(self, loops=1):
        FL.fluid_sequencer_remove_events(self.fseq, -1, -1, FLUID_SEQ_NOTEON)
        FL.fluid_sequencer_remove_events(self.fseq, -1, -1, FLUID_SEQ_TIMER)
        if loops != 0:
            self.loop = loops
            self.beat = 0
            self.nextnote = FL.fluid_sequencer_get_tick(self.fseq)
            self.scheduler()
            
    def timer(self, time):
        evt = FL.new_fluid_event()
        FL.fluid_event_set_source(evt, -1)
        FL.fluid_event_set_dest(evt, self.fseq_dest)
        FL.fluid_event_timer(evt, None)
        FL.fluid_sequencer_send_at(self.fseq, evt, int(time), 1)
        FL.delete_fluid_event(evt)

    def set_tempo(self, bpm):
        self.ticksperbeat = 1000 * 60 / bpm

    def delete(self):
        self.notes = []
        FL.fluid_sequencer_remove_events(self.fseq, -1, -1, -1)
        FL.fluid_sequencer_unregister_client(self.fseq, self.fseq_dest)
        FL.delete_fluid_sequencer(self.fseq)


class Arpeggiator(Sequencer):

    def __init__(self, synth, tdiv, swing, style, octaves):
        super().__init__(synth, [], tdiv, swing)
        self.style = style
        self.octaves = octaves
        self.keysdown = []

    def note(self, chan, key, vel):
        if vel > 0:
            self.keysdown.append(SequencerNote(chan, key, vel))
        else:
            for k in self.keysdown:
                if k.key == key:
                    self.keysdown.remove(k)
                    break
        self.notes = []
        for i in range(self.octaves):
            for k in self.keysdown:
                self.notes.append(SequencerNote(k.chan, k.key + i * 12, k.vel))
        if self.style == 'up' or self.style == 'both':
            self.notes.sort(key=lambda k: k.key)
        if self.style == 'down':
            self.notes.sort(key=lambda k: k.key, reverse=True)
        if self.style == 'both':
            self.notes += self.notes[-2:0:-1]
        if len(self.keysdown) == 1:
            self.play(loops=-1)
        elif len(self.keysdown) < 1:
            self.play(loops=0)


class Player:

    def __init__(self, synth, file, loops, barlength, chan, mask):
        self.fplayer = FL.new_fluid_player(synth.fsynth)
        if isinstance(file, list):
            for f in file: FL.fluid_player_add(self.fplayer, str(f).encode())
        else: FL.fluid_player_add(self.fplayer, str(file).encode())
        self.loops = list(zip(loops[::2], loops[1::2]))
        self.barlength = barlength
        self.pendingseek = SEEK_DONE
        self.lasttick = 0
        self.frouter_callback = fl_eventcallback(FL.fluid_midi_router_handle_midi_event)
        self.frouter = FL.new_fluid_midi_router(synth.st, self.frouter_callback, synth.frouter)
        FL.fluid_midi_router_clear_rules(self.frouter)
        for i in [EVENT_NAMES.index(x) for x in EVENT_NAMES if x not in mask]:
            rule = FL.new_fluid_midi_router_rule()
            if chan:
                FL.fluid_midi_router_rule_set_chan(rule, int(chan[0]), int(chan[1]), float(chan[2]), int(chan[3]))
            FL.fluid_midi_router_add_rule(self.frouter, rule, i)
        self.playback_callback = fl_eventcallback(FL.fluid_midi_router_handle_midi_event)
        FL.fluid_player_set_playback_callback(self.fplayer, self.playback_callback, self.frouter)
        if FLUID_VERSION >= (2, 2, 0):
            self.tickcallback = fl_tickcallback(self.looper)
            FL.fluid_player_set_tick_callback(self.fplayer, self.tickcallback, None)
        else:
            self.transport(0)

    if FLUID_VERSION >= (2, 2, 0):
        def transport(self, play, seek=None):
            if play == 0:
                FL.fluid_player_stop(self.fplayer)
            elif FL.fluid_player_get_status(self.fplayer) != FLUID_PLAYER_PLAYING:
                if seek != None:
                    maxticks = FL.fluid_player_get_total_ticks(self.fplayer)
                    if maxticks: seek = min(seek, maxticks)
                    FL.fluid_player_seek(self.fplayer, seek)
                    if seek > self.lasttick:
                        self.lasttick = self.pendingseek
                        self.pendingseek = SEEK_WAIT
                    else:
                        self.pendingseek = SEEK_DONE
                FL.fluid_player_play(self.fplayer)
            elif seek != None:
                self.pendingseek = seek

        def looper(self, data, tick):
            if self.pendingseek > SEEK_DONE:
                if tick % self.barlength < (tick - self.lasttick):
                    FL.fluid_player_seek(self.fplayer, self.pendingseek)
                    if self.pendingseek > tick:
                        self.lasttick = self.pendingseek
                        self.pendingseek = SEEK_WAIT
                    else:
                        self.lasttick = tick
                        self.pendingseek = SEEK_DONE
            elif self.pendingseek == SEEK_WAIT:
                if tick >= self.lasttick:
                    self.pendingseek = SEEK_DONE
                    self.lasttick = tick
            else:
                for start, end in self.loops:
                    if end < 0:
                        end = FL.fluid_player_get_total_ticks(self.fplayer) + end + 1
                    if self.lasttick < end <= tick:
                        if start < 0:
                            self.transport(0)
                            start = 0
                        FL.fluid_player_seek(self.fplayer, start)
                        self.lasttick = start
                        break
                else:
                    self.lasttick = tick

        def set_tempo(self, bpm=None):
            if bpm:
                usec = int(60000000.0 / bpm) # usec per quarter note (MIDI standard)
                FL.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_EXTERNAL_MIDI, usec)
            else:
                FL.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_INTERNAL, 1.0)
    else:
        def transport(self, play, seek=None):
            if play == 0:
                FL.fluid_player_stop(self.fplayer)
            else:
                if FLUID_VERSION >= (2, 0, 0) and seek != None:
                    maxticks = FL.fluid_player_get_total_ticks(self.fplayer)
                    if maxticks: seek = min(seek, maxticks)
                    FL.fluid_player_seek(self.fplayer, seek)
                FL.fluid_player_play(self.fplayer)

        def set_tempo(self, bpm=None):
            pass

    def delete(self):
        FL.fluid_player_stop(self.fplayer)
        FL.delete_fluid_player(self.fplayer)


class LadspaEffect:
    
    def __init__(self, synth, name, lib, plugin, channels, audio):
        self.synth = synth
        self.name = name
        self.lib = str(lib).encode()
        self.plugin = plugin.encode() if plugin else None
        self.channels = channels
        if audio == 'stereo':
            audio = 'Input L', 'Input R', 'Output L', 'Output R'
        elif audio == 'mono':
            audio = 'Input', 'Output'
        self.aports = [port.encode() for port in audio]
        self.fxunits = []
        self.portvals = {}

    def addfxunits(self):
        self.links = {}
        def addfxunit():
            fxname = f"{self.name}{len(self.fxunits)}".encode()
            if FL.fluid_ladspa_add_effect(self.synth.ladspa, fxname, self.lib, self.plugin) == FLUID_OK:
                self.fxunits.append(fxname)
                return True
            return False
        for hostports, midichannels in self.synth.hostports_mapping:
            if not self.channels & midichannels: continue
            if len(self.aports) == 4: # stereo effect
                if addfxunit():
                    self.links[hostports] = self.fxunits[-1:] * 2, self.aports[0:2], self.aports[2:4]
            if len(self.aports) == 2: # mono effect
                if addfxunit() and addfxunit():
                    self.links[hostports] = self.fxunits[-2:], self.aports[0:1] * 2, self.aports[1:2] * 2
        
    def link(self, hostports, inputs, outputs):
        for fxunit, fxin, fxout, inp, outp in zip(*self.links[hostports], inputs, outputs):
            FL.fluid_ladspa_effect_link(self.synth.ladspa, fxunit, fxin, inp.encode())
            FL.fluid_ladspa_effect_link(self.synth.ladspa, fxunit, fxout, outp.encode())

    def setcontrol(self, port, val):
        self.portvals[port] = val
        for fxunit in self.fxunits:
            FL.fluid_ladspa_effect_set_control(self.synth.ladspa, fxunit, port.encode(), c_float(val))


class Synth:

    def __init__(self, **settings):
        self.st = FL.new_fluid_settings()
        for opt, val in settings.items():
            self.setting(opt, val)
        self.fsynth = FL.new_fluid_synth(self.st)
        FL.new_fluid_audio_driver(self.st, self.fsynth)
        self.frouter_callback = fl_eventcallback(FL.fluid_synth_handle_midi_event)
        self.frouter = FL.new_fluid_midi_router(self.st, self.frouter_callback, self.fsynth)
        self.custom_router_callback = fl_eventcallback(self.custom_midi_router)
        FL.new_fluid_midi_driver(self.st, self.custom_router_callback, None)      
        self.sfid = {}
        self.xrules = []
        self.players = {}
        self.msg_callback = None
        if LADSPA_SUPPORT:
            nports = self.get_setting('synth.audio-groups')
            nchan = self.get_setting('synth.midi-channels')
            if nports == 1:
                hostports = [('Main:L', 'Main:R')]
            else:
                hostports = [(f'Main:L{i + 1}', f'Main:R{i + 1}') for i in range(nports)]
            midichannels = [set(range(i, nchan, nports)) for i in range(nports)]
            self.hostports_mapping = list(zip(hostports, midichannels))
            self.ladspa = FL.fluid_synth_get_ladspa_fx(self.fsynth)
            self.ladspafx = {}
            
    def reset(self):
        FL.fluid_synth_system_reset(self.fsynth)

    def custom_midi_router(self, data, event):
        mevent = MidiEvent(event)
        if mevent.type == None:
            return FL.fluid_midi_router_handle_midi_event(self.frouter, event)            
        for rule in self.xrules:
            if not rule.applies(mevent):
                continue
            res = rule.apply(mevent)
            if isinstance(res, MidiEvent):
                FL.fluid_synth_handle_midi_event(self.fsynth, res.event)
                continue
            if hasattr(res, 'fluidsetting'):
                self.setting(res.fluidsetting, res.val)
            elif hasattr(res, 'sequencer'):
                if res.sequencer in self.players:
                    self.players[res.sequencer].play(res.val)
            elif hasattr(res, 'arpeggiator'):
                if res.arpeggiator in self.players:
                    self.players[res.arpeggiator].note(res.chan, res.par1, res.val)
            elif hasattr(res, 'player'):
                if res.player in self.players:
                    self.players[res.player].transport(res.val, getattr(res, 'tick', None))
            elif hasattr(res, 'tempo'):
                if res.tempo in self.players:
                    self.players[res.tempo].set_tempo(res.val)
            elif hasattr(res, 'ladspafx'):
                if res.ladspafx in getattr(self, 'ladspafx', {}):
                    self.ladspafx[res.ladspafx].setcontrol(res.port, res.val)
            else:
                if self.msg_callback: self.msg_callback(res)
        if self.msg_callback: self.msg_callback(MidiMessage(mevent))
        return FL.fluid_midi_router_handle_midi_event(self.frouter, mevent.event)

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
        i = FL.fluid_synth_sfload(self.fsynth, str(sfont).encode(), False)
        if i == FLUID_FAILED:
            return False
        self.sfid[sfont] = i
        return True

    def unload_soundfont(self, sfont):
        if FL.fluid_synth_sfunload(self.fsynth, self.sfid[sfont], False) == FLUID_FAILED:
            return False
        del self.sfid[sfont]
        return True

    def program_select(self, chan, sfont, bank, prog):
        if sfont not in self.sfid:
            return False
        x = FL.fluid_synth_program_select(self.fsynth, chan, self.sfid[sfont], bank, prog)
        if x == FLUID_FAILED:
            return False
        return True

    def program_unset(self, chan):
        FL.fluid_synth_unset_program(self.fsynth, chan)

    def program_info(self, chan):
        i = c_int()
        bank = c_int()
        prog = c_int()
        FL.fluid_synth_get_program(self.fsynth, chan, byref(i), byref(bank), byref(prog))
        if i.value not in self.sfid.values():
            return None
        sfont = {v: k for k, v in self.sfid.items()}[i.value]
        return sfont, bank.value, prog.value

    def send_event(self, type, chan, par1, par2=None):
        newevent = MidiEvent(FL.new_fluid_midi_event())
        newevent.type = MIDI_TYPES[EVENT_NAMES.index(type)]
        newevent.chan = chan
        newevent.par1 = par1
        newevent.par2 = par2
        self.custom_midi_router(None, newevent.event)

    def send_sysex(self, data):
        newevent = MidiEvent(FL.new_fluid_midi_event())
        syxdata = (c_int * len(data))(*data)
        FL.fluid_midi_event_set_sysex(newevent.event, syxdata, sizeof(syxdata), True)
        self.custom_midi_router(None, newevent.event)

    def send_cc(self, chan, ctrl, val):
        FL.fluid_synth_cc(self.fsynth, chan, ctrl, val)

    def get_cc(self, chan, ctrl):
        val = c_int()
        FL.fluid_synth_get_cc(self.fsynth, chan, ctrl, byref(val))
        return val.value

    def router_clear(self):
        FL.fluid_midi_router_clear_rules(self.frouter)
        self.xrules = []

    def router_default(self):
        FL.fluid_midi_router_set_default_rules(self.frouter)
        self.xrules = []

    def router_addrule(self, type, chan, par1, par2, **apars):
        if 'type2' in apars:
            self.xrules.insert(0, TransRule(type, chan, par1, par2, apars['type2']))
        elif apars:
            self.xrules.insert(0, ExtRule(type, chan, par1, par2, **apars))
            if 'arpeggiator' in apars:
                self.xrules.insert(0, ExtRule('noteoff', chan, par1, (0, 127, 0, 0), **apars))
        else:
            rule = FL.new_fluid_midi_router_rule()
            if chan:
                FL.fluid_midi_router_rule_set_chan(rule, int(chan[0]), int(chan[1]), float(chan[2]), int(chan[3]))
            if par1:
                FL.fluid_midi_router_rule_set_param1(rule, int(par1[0]), int(par1[1]), float(par1[2]), int(par1[3]))
            if par2:
                FL.fluid_midi_router_rule_set_param2(rule, int(par2[0]), int(par2[1]), float(par2[2]), int(par2[3]))
            FL.fluid_midi_router_add_rule(self.frouter, rule, EVENT_NAMES.index(type))

    def players_clear(self, save=[]):
        for name in [x for x in self.players if x not in save]:
            self.players[name].delete()
            del self.players[name]

    def sequencer_add(self, name, notes, tdiv=8, swing=0.5, tempo=120):
        if name not in self.players:
            self.players[name] = Sequencer(self, notes, tdiv, swing)
            self.players[name].set_tempo(tempo)

    def arpeggiator_add(self, name, tdiv=8, swing=0.5, style='', octaves=1, tempo=120):
        if name not in self.players:
            self.players[name] = Arpeggiator(self, tdiv, swing, style, octaves)
            self.players[name].set_tempo(tempo)

    def player_add(self, name, file, loops=[], barlength=1, chan=None, mask=['prog'], tempo=0):
        if name not in self.players:
            self.players[name] = Player(self, file, loops, barlength, chan, mask)
            if tempo > 0:
                self.players[name].set_tempo(tempo)

    if FLUID_VERSION >= (2, 0, 0):
        def get_sfpresets(self, sfont):
            presets = []
            sfont_obj = FL.fluid_synth_get_sfont_by_id(self.fsynth, self.sfid[sfont])
            FL.fluid_sfont_iteration_start(sfont_obj)
            while True:
                p = FL.fluid_sfont_iteration_next(sfont_obj)
                if p == None: break
                presets.append(PresetInfo(p))
            return presets
    else:
        def get_sfpresets(self, sfont):
            presets = []
            for bank in range(129):
                for prog in range(128):
                    if not self.program_select(0, sfont, bank, prog): continue
                    info = fluid_synth_channel_info_t()
                    FL.fluid_synth_get_channel_info(self.fsynth, 0, byref(info))
                    presets.append(PresetInfo(info.name.decode(), bank, prog))
            return presets

    if LADSPA_SUPPORT:
        def fxchain_clear(self, save=[]):
            clear = [x for x in self.ladspafx if x not in save]
            if clear:
                FL.fluid_ladspa_reset(self.ladspa)
                for name in clear:
                    del self.ladspafx[name]
                for ladpsafx in self.ladspafx.values():
                    ladpsafx.fxunits = []

        def fxchain_add(self, name, lib, plugin=None, chan=None, audio='stereo', vals={}):
            if name not in self.ladspafx:
                if FL.fluid_ladspa_is_active(self.ladspa):
                    FL.fluid_ladspa_reset(self.ladspa)
                self.ladspafx[name] = LadspaEffect(self, name, lib, plugin, chan, audio)
            self.ladspafx[name].portvals.update(vals)

        def fxchain_connect(self):
            if self.ladspafx == {} or FL.fluid_ladspa_is_active(self.ladspa): return
            for name in self.ladspafx:
                self.ladspafx[name].addfxunits()
                for ctrl, val in self.ladspafx[name].portvals.items():
                    self.ladspafx[name].setcontrol(ctrl, val)
            b = 0
            for hostports, midichannels in self.hostports_mapping:
                lastports = hostports
                for name, effect in self.ladspafx.items():
                    if hostports not in effect.links: continue
                    if name != list(self.ladspafx)[-1]:
                        buffers = [f"buffer{b}", f"buffer{b + 1}"]
                        b += 2
                        FL.fluid_ladspa_add_buffer(self.ladspa, buffers[0].encode())
                        FL.fluid_ladspa_add_buffer(self.ladspa, buffers[1].encode())
                        effect.link(hostports, lastports, buffers)
                        lastports = buffers
                    else:
                        effect.link(hostports, lastports, hostports)
            FL.fluid_ladspa_activate(self.ladspa)
    else:
        def fxchain_clear(self):
            pass

        def fxchain_add(self, name, lib, plugin=None, chan=None, audio='stereo', vals={}):
            pass

        def fxchain_connect(self):
            pass
