"""
Description: classes to provide an interface and some custom MIDI routing for fluidsynth via ctypes
"""
from ctypes import *
from ctypes.util import find_library

FLUID_OK = 0
FLUID_FAILED = -1
FLUID_NUM_TYPE = 0
FLUID_INT_TYPE = 1
FLUID_STR_TYPE = 2
FLUID_SEQ_NOTEON = 1
FLUID_SEQ_TIMER = 17
FLUID_SEQ_UNREGISTERING = 21
FLUID_PLAYER_TEMPO_INTERNAL = 0
FLUID_PLAYER_TEMPO_EXTERNAL_MIDI = 2
FLUID_PLAYER_PLAYING = 1
FLUID_PLAYER_DONE = 3
MIDI_TYPES = {'note': 0x90, 'cc': 0xb0, 'prog': 0xc0, 'pbend': 0xe0, 'cpress': 0xd0, 'kpress': 0xa0, 'noteoff': 0x80,
              'clock': 0xf8, 'start': 0xfa, 'continue': 0xfb, 'stop': 0xfc}
MIDI_VOICE_2PAR = 'note', 'cc', 'kpress', 'noteoff'
MIDI_VOICE_1PAR = 'prog', 'pbend', 'cpress'
MIDI_REALTIME = 'clock', 'start', 'continue', 'stop'
SEEK_DONE = -1
SEEK_WAIT = -2

fslib = find_library('fluidsynth') or find_library('libfluidsynth-3')
if fslib is None:
    raise ImportError("Couldn't find the FluidSynth library.")
FS = CDLL(fslib)
def specfunc(func, restype, *argtypes):
    func.restype = restype
    func.argtypes = argtypes
    return func

# logging
fl_logfunction = CFUNCTYPE(c_void_p, c_int, c_char_p, c_void_p)
specfunc(FS.fluid_set_log_function, c_void_p, c_int, fl_logfunction, c_void_p)
nolog = fl_logfunction(lambda level, message, data: None)
for lvl in range(1,5):
    FS.fluid_set_log_function(lvl, nolog, None)

# settings
specfunc(FS.new_fluid_settings, c_void_p)
specfunc(FS.fluid_settings_get_type, c_int, c_void_p, c_char_p)
specfunc(FS.fluid_settings_getint, c_int, c_void_p, c_char_p, POINTER(c_int))
specfunc(FS.fluid_settings_getnum, c_int, c_void_p, c_char_p, POINTER(c_double))
specfunc(FS.fluid_settings_copystr, c_int, c_void_p, c_char_p, c_char_p, c_int)
specfunc(FS.fluid_settings_setint, c_int, c_void_p, c_char_p, c_int)
specfunc(FS.fluid_settings_setnum, c_int, c_void_p, c_char_p, c_double)
specfunc(FS.fluid_settings_setstr, c_int, c_void_p, c_char_p, c_char_p)

# synth
fl_eventcallback = CFUNCTYPE(c_int, c_void_p, c_void_p)
specfunc(FS.new_fluid_synth, c_void_p, c_void_p)
specfunc(FS.new_fluid_audio_driver, c_void_p, c_void_p, c_void_p)
specfunc(FS.new_fluid_midi_router, c_void_p, c_void_p, fl_eventcallback, c_void_p)
specfunc(FS.new_fluid_midi_driver, c_void_p, c_void_p, fl_eventcallback, c_void_p)
specfunc(FS.fluid_synth_handle_midi_event, c_int, c_void_p, c_void_p)
specfunc(FS.fluid_synth_system_reset, c_int, c_void_p)
specfunc(FS.fluid_synth_sfload, c_int, c_void_p, c_char_p, c_int)
specfunc(FS.fluid_synth_sfunload, c_int, c_void_p, c_int, c_int)
specfunc(FS.fluid_synth_get_sfont_by_id, c_void_p, c_void_p, c_int)
specfunc(FS.fluid_synth_program_select, c_int, c_void_p, c_int, c_int, c_int, c_int)
specfunc(FS.fluid_synth_unset_program, c_int, c_void_p, c_int)
specfunc(FS.fluid_synth_get_program, c_int, c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int))
specfunc(FS.fluid_synth_cc, c_int, c_void_p, c_int, c_int, c_int)
specfunc(FS.fluid_synth_get_cc, c_int, c_void_p, c_int, c_int, POINTER(c_int))

# soundfonts
specfunc(FS.fluid_sfont_iteration_start, None, c_void_p)
specfunc(FS.fluid_sfont_iteration_next, c_void_p, c_void_p)
specfunc(FS.fluid_preset_get_name, c_char_p, c_void_p)
specfunc(FS.fluid_preset_get_banknum, c_int, c_void_p)
specfunc(FS.fluid_preset_get_num, c_int, c_void_p)

# midi router
specfunc(FS.new_fluid_midi_router_rule, c_void_p)
specfunc(FS.fluid_midi_router_add_rule, c_int, c_void_p, c_void_p, c_int)
specfunc(FS.fluid_midi_router_clear_rules, c_int, c_void_p)
specfunc(FS.fluid_midi_router_set_default_rules, c_int, c_void_p)
specfunc(FS.fluid_midi_router_rule_set_chan, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FS.fluid_midi_router_rule_set_param1, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FS.fluid_midi_router_rule_set_param2, None, c_void_p, c_int, c_int, c_float, c_int)
specfunc(FS.fluid_midi_router_handle_midi_event, c_int, c_void_p, c_void_p)

# midi events
specfunc(FS.new_fluid_midi_event, c_void_p)
specfunc(FS.delete_fluid_event, None, c_void_p)
specfunc(FS.fluid_midi_event_get_type, c_int, c_void_p)
specfunc(FS.fluid_midi_event_get_channel, c_int, c_void_p)
fl_midi_event_get_par1 = specfunc(FS.fluid_midi_event_get_key, c_int, c_void_p)
fl_midi_event_get_par2 = specfunc(FS.fluid_midi_event_get_velocity, c_int, c_void_p)
specfunc(FS.fluid_midi_event_set_type, c_int, c_void_p, c_int)
specfunc(FS.fluid_midi_event_set_channel, c_int, c_void_p, c_int)
fl_midi_event_set_par1 = specfunc(FS.fluid_midi_event_set_key, c_int, c_void_p, c_int)
fl_midi_event_set_par2 = specfunc(FS.fluid_midi_event_set_velocity, c_int, c_void_p, c_int)
specfunc(FS.fluid_midi_event_set_sysex, c_int, c_void_p, c_void_p, c_int, c_int)

# sequencer events
specfunc(FS.new_fluid_event, c_void_p)
specfunc(FS.delete_fluid_event, None, c_void_p)
specfunc(FS.fluid_event_noteon, None, c_void_p, c_int, c_int, c_int)
specfunc(FS.fluid_event_noteoff, None, c_void_p, c_int, c_int)
specfunc(FS.fluid_event_set_source, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_set_dest, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_timer, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_get_type, c_int, c_void_p)

# sequencer
fl_seqcallback = CFUNCTYPE(None, c_uint, c_void_p, c_void_p, c_void_p)
specfunc(FS.new_fluid_sequencer2, c_void_p, c_int)
specfunc(FS.delete_fluid_sequencer, None, c_void_p)
specfunc(FS.fluid_sequencer_register_fluidsynth, c_short, c_void_p, c_void_p)
specfunc(FS.fluid_sequencer_register_client, c_short, c_void_p, c_char_p, fl_seqcallback, c_void_p)
specfunc(FS.fluid_sequencer_unregister_client, None, c_void_p, c_short)
specfunc(FS.fluid_sequencer_set_time_scale, None, c_void_p, c_double)
specfunc(FS.fluid_sequencer_send_at, c_int, c_void_p, c_void_p, c_uint, c_int)
specfunc(FS.fluid_sequencer_remove_events, None, c_void_p, c_short, c_short, c_int)
specfunc(FS.fluid_sequencer_get_tick, c_uint, c_void_p)

# player
fl_tickcallback = CFUNCTYPE(None, c_void_p, c_uint)
specfunc(FS.new_fluid_player, c_void_p, c_void_p)
specfunc(FS.delete_fluid_player, None, c_void_p)
specfunc(FS.fluid_player_add, c_int, c_void_p, c_char_p)
specfunc(FS.fluid_player_set_playback_callback, c_int, c_void_p, fl_eventcallback, c_void_p)
specfunc(FS.fluid_player_set_tick_callback, c_int, c_void_p, fl_tickcallback, c_void_p)
specfunc(FS.fluid_player_set_tempo, c_int, c_void_p, c_int, c_double)
specfunc(FS.fluid_player_play, c_int, c_void_p)
specfunc(FS.fluid_player_stop, c_int, c_void_p)
specfunc(FS.fluid_player_seek, c_int, c_void_p, c_int)
specfunc(FS.fluid_player_get_status, c_int, c_void_p)
specfunc(FS.fluid_player_get_current_tick, c_int, c_void_p)

try:
    specfunc(FS.fluid_ladspa_activate, c_void_p, c_void_p)
    specfunc(FS.fluid_ladspa_is_active, c_int, c_void_p)
    specfunc(FS.fluid_ladspa_reset, c_int, c_void_p)
    specfunc(FS.fluid_ladspa_add_effect, c_int, c_void_p, c_char_p, c_char_p, c_char_p)
    specfunc(FS.fluid_ladspa_add_buffer, c_int, c_void_p, c_char_p)
    specfunc(FS.fluid_ladspa_effect_can_mix, c_int, c_void_p, c_char_p)
    specfunc(FS.fluid_ladspa_effect_set_mix, c_int, c_void_p, c_char_p, c_int, c_float)
    specfunc(FS.fluid_ladspa_effect_set_control, c_int, c_void_p, c_char_p, c_char_p, c_float)
    specfunc(FS.fluid_ladspa_effect_link, c_int, c_void_p, c_char_p, c_char_p, c_char_p)
    specfunc(FS.fluid_synth_get_ladspa_fx, c_void_p, c_void_p)
    LADSPA_SUPPORT = True
except AttributeError:
    LADSPA_SUPPORT = False


class MidiEvent:

    def __init__(self, event):
        self.event = event

    @property
    def type(self):
        b = FS.fluid_midi_event_get_type(self.event)
        if b == 0x90 and self.par2 == 0: b = 0x80
        return {v: k for k, v in MIDI_TYPES.items()}.get(b, None)
    @type.setter
    def type(self, n):
        n = MIDI_TYPES.get(n, None)
        FS.fluid_midi_event_set_type(self.event, n)

    @property
    def chan(self): return FS.fluid_midi_event_get_channel(self.event)
    @chan.setter
    def chan(self, v): FS.fluid_midi_event_set_channel(self.event, v)
    
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
        self.type = mevent.type
        self.chan = mevent.chan
        self.par1 = mevent.par1
        self.par2 = mevent.par2
        
    def __repr__(self):
        return str(self.__dict__)


class ExtMessage(MidiMessage):

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

    def __iter__(self):
        return iter((int(self.min), int(self.max), float(self.mul), int(self.add)))

    def __repr__(self):
        return str(self.__dict__)


class TransRule:

    def __init__(self, type, chan, par1, par2):
        self.hastype = type[0]
        self.newtype = type[-1]
        self.chan = Route(*chan) if chan else None
        self.par1 = Route(*par1) if par1 else None
        self.par2 = Route(*par2) if par2 else None

    def __repr__(self):
        return str(self.__dict__)

    def applies(self, mevent):
        if self.hastype != mevent.type:
            return False
        if self.hastype in MIDI_REALTIME:
            return True
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
        if self.hastype in MIDI_VOICE_2PAR and self.par2 != None:
            if self.par2.min > self.par2.max:
                if self.par2.min < mevent.par2 < self.par2.max:
                    return False
            else:
                if not (self.par2.min <= mevent.par2 <= self.par2.max):
                    return False
        return True

    def apply(self, mevent):
        newevent = MidiEvent(FS.new_fluid_midi_event())
        newevent.type = self.newtype
        newevent.chan = mevent.chan
        newevent.par1 = mevent.par1
        newevent.par2 = mevent.par2
        if self.hastype in MIDI_REALTIME:
            if self.chan != None: newevent.chan = self.chan.min
            if self.par1 != None: newevent.par1 = self.par1.min
            if self.par2 != None: newevent.par2 = self.par2.min
        else:
            if self.chan != None: newevent.chan = int(mevent.chan * self.chan.mul + self.chan.add + 0.5)
        if self.hastype in MIDI_VOICE_2PAR:
            if self.newtype in MIDI_VOICE_2PAR:
                if self.par1 != None: newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
                if self.par2 != None: newevent.par2 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
            elif self.newtype in MIDI_VOICE_1PAR:
                if self.par2 == None: newevent.par1 = mevent.par2
                else: newevent.par1 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
        elif self.hastype in MIDI_VOICE_1PAR:
            if self.newtype in MIDI_VOICE_1PAR:
                if self.par1 != None: newevent.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
            elif self.newtype in MIDI_VOICE_2PAR:
                if self.par2 != None: newevent.par1 = self.par2.min
                if self.par1 == None: newevent.par2 = mevent.par1
                else: newevent.par2 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
        return newevent


class ExtRule(TransRule):

    def __init__(self, type, chan, par1, par2, **apars):
        super().__init__(type, chan, par1, par2)
        for attr, val in apars.items():
            setattr(self, attr, val)

    def apply(self, mevent):
        msg = ExtMessage(mevent, extrule=self)
        if self.chan != None: msg.chan = int(mevent.chan * self.chan.mul + self.chan.add + 0.5)
        if self.par1 != None: msg.par1 = int(mevent.par1 * self.par1.mul + self.par1.add + 0.5)
        if self.par2 != None: msg.par2 = int(mevent.par2 * self.par2.mul + self.par2.add + 0.5)
        if self.hastype in MIDI_VOICE_2PAR:
            msg.val = mevent.par2
            if self.par2: msg.val = msg.val * self.par2.mul + self.par2.add
        elif self.hastype in MIDI_VOICE_1PAR:
            msg.val = mevent.par1
            if self.par1: msg.val = msg.val * self.par1.mul + self.par1.add
        elif self.hastype == 'clock':
            msg.val = 0.041666664
        elif self.hastype in ('start', 'continue'):
            msg.val = self.par1.min if self.par1 else -1
        elif self.hastype == 'stop':
            msg.val = self.par1.min if self.par1 else 0
        return msg


class PresetInfo:
    
    def __init__(self, preset_obj):        
        self.bank = FS.fluid_preset_get_banknum(preset_obj)
        self.prog = FS.fluid_preset_get_num(preset_obj)
        self.name = FS.fluid_preset_get_name(preset_obj).decode()

    def __repr__(self):
        return str(self.__dict__)


class SequencerNote:

    def __init__(self, chan, key, vel):
        self.chan = chan
        self.key = key
        self.vel = vel

    def schedule(self, seq, timeon, timeoff, accent=1):
        evt = FS.new_fluid_event()
        FS.fluid_event_set_source(evt, -1)
        FS.fluid_event_set_dest(evt, seq.fsynth_id)
        FS.fluid_event_noteon(evt, self.chan, self.key, int(min(self.vel * accent, 127)))
        FS.fluid_sequencer_send_at(seq.fseq, evt, int(timeon), 1)
        FS.delete_fluid_event(evt)
        evt = FS.new_fluid_event()
        FS.fluid_event_set_source(evt, -1)
        FS.fluid_event_set_dest(evt, seq.fsynth_id)
        FS.fluid_event_noteoff(evt, int(self.chan), int(self.key))
        FS.fluid_sequencer_send_at(seq.fseq, evt, int(timeoff), 1)
        FS.delete_fluid_event(evt)


class Sequencer:

    def __init__(self, synth, notes, tdiv, swing, groove):
        self.fseq = synth.fseq
        self.fsynth_id = synth.fsynth_id
        self.callback = fl_seqcallback(self.scheduler)
        self.seq_id = FS.fluid_sequencer_register_client(self.fseq, b'seq', self.callback, None)
        self.notes = [SequencerNote(chan, key, vel) for _, chan, key, vel in notes]
        self.tdiv = tdiv
        self.swing = swing
        self.groove = groove
        self.ticksperbeat = 500 # default 120bpm at 1000 ticks/sec
        self.beat = 0

    def scheduler(self, time=None, event=None, fseq=None, data=None):
        if event and FS.fluid_event_get_type(event) == FLUID_SEQ_UNREGISTERING:
            return
        if not self.notes: return
        dur = self.ticksperbeat * 4 / self.tdiv
        if self.tdiv >= 8 and self.tdiv % 3:
            if self.beat % 2: dur *= 2 * (1 - self.swing)
            else: dur *= 2 * self.swing
        pos = self.beat % len(self.notes)
        if isinstance(self.groove, list): accent = self.groove[self.beat % len(self.groove)]
        elif self.beat % 2: accent = 1
        else: accent = self.groove
        for note in self.notes[pos] if isinstance(self.notes[pos], list) else [self.notes[pos]]:
            note.schedule(self, self.nextnote, self.nextnote + dur, accent)
        if pos == len(self.notes) - 1:
            self.loop -= 1
        if self.loop != 0:
            self.timer(self.nextnote + 0.99 * dur)
            self.nextnote += dur
            self.beat += 1

    def play(self, loops=1):
        FS.fluid_sequencer_remove_events(self.fseq, -1, self.seq_id, FLUID_SEQ_TIMER)
        if loops != 0:
            self.loop = loops
            self.beat = 0
            self.nextnote = FS.fluid_sequencer_get_tick(self.fseq)
            self.scheduler()
            
    def timer(self, time):
        evt = FS.new_fluid_event()
        FS.fluid_event_set_source(evt, -1)
        FS.fluid_event_set_dest(evt, self.seq_id)
        FS.fluid_event_timer(evt, None)
        FS.fluid_sequencer_send_at(self.fseq, evt, int(time), 1)
        FS.delete_fluid_event(evt)

    def set_tempo(self, bpm):
        # default fluid_sequencer time scale is 1000 ticks per second
        self.ticksperbeat = 1000 * 60 / bpm

    def dismiss(self):
        self.notes = []
        self.play(0)
        FS.fluid_sequencer_unregister_client(self.fseq, self.seq_id)


class Arpeggiator(Sequencer):

    def __init__(self, synth, tdiv, swing, groove, style, octaves):
        super().__init__(synth, [], tdiv, swing, groove)
        self.style = style
        self.octaves = octaves
        self.keysdown = []

    def note(self, chan, key, vel):
        if vel > 0:
            self.keysdown.append(SequencerNote(chan, key, vel))
            nd = len(self.keysdown)
        else:
            for k in self.keysdown:
                if k.key == key:
                    self.keysdown.remove(k)
                    break
            nd = -len(self.keysdown)
        if self.style in ('up', 'down', 'both'):
            self.keysdown.sort(key=lambda n: n.key)
        self.notes = []
        for i in range(self.octaves):
            for n in self.keysdown:
                self.notes.append(SequencerNote(n.chan, n.key + i * 12, n.vel))
        if self.style == 'down':
            self.notes.reverse()
        elif self.style == 'both':
            self.notes += self.notes[-2:0:-1]
        elif self.style == 'chord':
            self.notes = [self.notes]
            if self.beat < 2:
                self.play(loops=-1)
        if nd == 1:
            self.play(loops=-1)
        elif nd == 0:
            self.play(loops=0)


class MidiPlayer:

    def __init__(self, synth, file, loops, barlength, chan, mask):
        self.fplayer = FS.new_fluid_player(synth.fsynth)
        for f in file if isinstance(file, list) else [file]:
            FS.fluid_player_add(self.fplayer, str(f).encode())
        self.loops = list(zip(loops[::2], loops[1::2]))
        self.barlength = barlength
        self.seek = None
        self.seek_now = False
        self.lasttick = 0
        self.frouter_callback = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
        self.frouter = FS.new_fluid_midi_router(synth.st, self.frouter_callback, synth.frouter)
        FS.fluid_midi_router_clear_rules(self.frouter)
        for rtype in set(list(MIDI_TYPES)[:6]) - set(mask):
            rule = FS.new_fluid_midi_router_rule()
            if chan: FS.fluid_midi_router_rule_set_chan(rule, *Route(*chan))
            FS.fluid_midi_router_add_rule(self.frouter, rule, list(MIDI_TYPES).index(rtype))
        self.playback_callback = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
        FS.fluid_player_set_playback_callback(self.fplayer, self.playback_callback, self.frouter)
        self.tickcallback = fl_tickcallback(self.looper)
        FS.fluid_player_set_tick_callback(self.fplayer, self.tickcallback, None)

    def transport(self, play, seek=None):
        if play == 0:
            FS.fluid_player_stop(self.fplayer)
        elif FS.fluid_player_get_status(self.fplayer) == FLUID_PLAYER_PLAYING:
            if seek != None:
                self.seek = seek
                self.seek_now = False if play < 0 else True
        else:
            if seek != None:
                self.seek = seek
                self.seek_now = True
            if play > 0: FS.fluid_player_play(self.fplayer)

    def looper(self, data, tick):
        if self.seek != None:
            if self.seek_now or tick % self.barlength < (tick - self.lasttick):
                if str(self.seek).endswith('+'):
                    self.seek = FS.fluid_player_get_current_tick(self.fplayer) + int(self.seek[:-1])
                elif str(self.seek).endswith('-'):
                    self.seek = FS.fluid_player_get_current_tick(self.fplayer) - int(self.seek[:-1])
                if FS.fluid_player_seek(self.fplayer, self.seek) == FLUID_OK:
                    self.lasttick = self.seek
                self.seek = None
        elif self.lasttick < tick:
            for start, end in self.loops:
                if self.lasttick < end <= tick:
                    if start < 0:
                        self.transport(0)
                        start = 0
                    if FS.fluid_player_seek(self.fplayer, start) == FLUID_OK:
                        self.lasttick = start
                    break
            else:
                self.lasttick = tick

    def set_tempo(self, bpm=None):
        if bpm:
            usec = int(60000000.0 / bpm) # usec per quarter note (MIDI standard)
            FS.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_EXTERNAL_MIDI, usec)
        else:
            FS.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_INTERNAL, 1.0)

    def dismiss(self):
        FS.fluid_player_stop(self.fplayer)
        FS.delete_fluid_player(self.fplayer)


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
            if FS.fluid_ladspa_add_effect(self.synth.ladspa, fxname, self.lib, self.plugin) != FLUID_OK: return False
            if FS.fluid_ladspa_effect_can_mix(self.synth.ladspa, fxname):
                FS.fluid_ladspa_effect_set_mix(self.synth.ladspa, fxname, 1, 1.0)
            self.fxunits.append(fxname)
            return True
        for midichannels, hostports, outports in self.synth.port_mapping:
            if self.channels and not self.channels & midichannels: continue
            if len(self.aports) == 4: # stereo effect
                if addfxunit():
                    self.links[hostports] = self.fxunits[-1:] * 2, self.aports[0:2], self.aports[2:4]
            if len(self.aports) == 2: # mono effect
                if addfxunit() and addfxunit():
                    self.links[hostports] = self.fxunits[-2:], self.aports[0:1] * 2, self.aports[1:2] * 2
        
    def link(self, hostports, inputs, outputs):
        for fxunit, fxin, fxout, inp, outp in zip(*self.links[hostports], inputs, outputs):
            FS.fluid_ladspa_effect_link(self.synth.ladspa, fxunit, fxin, inp.encode())
            FS.fluid_ladspa_effect_link(self.synth.ladspa, fxunit, fxout, outp.encode())

    def setcontrol(self, port, val):
        self.portvals[port] = val
        for fxunit in self.fxunits:
            FS.fluid_ladspa_effect_set_control(self.synth.ladspa, fxunit, port.encode(), c_float(val))


class Synth:

    def __init__(self, **settings):
        self.st = FS.new_fluid_settings()
        for opt, val in settings.items():
            self.setting(opt, val)
        self.fsynth = FS.new_fluid_synth(self.st)
        self.fseq = FS.new_fluid_sequencer2(0)
        self.fsynth_id = FS.fluid_sequencer_register_fluidsynth(self.fseq, self.fsynth)
        FS.new_fluid_audio_driver(self.st, self.fsynth)
        self.frouter_callback = fl_eventcallback(FS.fluid_synth_handle_midi_event)
        self.frouter = FS.new_fluid_midi_router(self.st, self.frouter_callback, self.fsynth)
        self.custom_router_callback = fl_eventcallback(self.custom_midi_router)
        FS.new_fluid_midi_driver(self.st, self.custom_router_callback, None)
        self.clocks = [0, 0]
        self.xrules = []
        self.sfid = {}
        self.players = {}
        self.msg_callback = None
        if LADSPA_SUPPORT:
            nports = self.get_setting('synth.audio-groups')
            nchan = self.get_setting('synth.audio-channels')
            nmidi = self.get_setting('synth.midi-channels')
            if nports == 1:
                hostports = outports = [('Main:L', 'Main:R')]
            else:
                hostports = [(f'Main:L{i}', f'Main:R{i}') for i in range(1, nports + 1)]
                outports = hostports[0:nchan] * nports
            midichannels = [set(range(i, nmidi, nports)) for i in range(nports)]
            self.port_mapping = list(zip(midichannels, hostports, outports))
            self.ladspa = FS.fluid_synth_get_ladspa_fx(self.fsynth)
            self.ladspafx = {}
            
    def reset(self):
        FS.fluid_synth_system_reset(self.fsynth)

    def custom_midi_router(self, data, event):
        mevent = MidiEvent(event)
        t = FS.fluid_sequencer_get_tick(self.fseq)
        dt = 0
        for rule in self.xrules:
            if not rule.applies(mevent):
                continue
            res = rule.apply(mevent)
            if isinstance(res, MidiEvent):
                FS.fluid_synth_handle_midi_event(self.fsynth, res.event)
                continue
            if hasattr(res, 'fluidsetting'):
                self.setting(res.fluidsetting, res.val)
            elif hasattr(res, 'sequencer'):
                if res.sequencer in self.players:
                    self.players[res.sequencer].play(res.val)
            elif hasattr(res, 'arpeggiator'):
                if res.arpeggiator in self.players:
                    self.players[res.arpeggiator].note(res.chan, res.par1, res.val)
            elif hasattr(res, 'midiplayer'):
                if res.midiplayer in self.players:
                    self.players[res.midiplayer].transport(res.val, getattr(res, 'tick', None))
            elif hasattr(res, 'tempo'):
                if res.tempo in self.players:
                    self.players[res.tempo].set_tempo(res.val)
            elif hasattr(res, 'sync'):
                if res.sync in self.players:
                    dt, dt2 = t - self.clocks[0], self.clocks[0] - self.clocks[1]
                    bpm = 1000 * 60 * res.val / dt
                    if dt2/dt > 0.5: self.players[res.sync].set_tempo(bpm)
            elif hasattr(res, 'ladspafx'):
                if res.ladspafx in getattr(self, 'ladspafx', {}):
                    self.ladspafx[res.ladspafx].setcontrol(res.port, res.val)
            else:
                if self.msg_callback: self.msg_callback(res)
        if dt > 0: self.clocks = t, self.clocks[0]
        if self.msg_callback: self.msg_callback(MidiMessage(mevent))
        return FS.fluid_midi_router_handle_midi_event(self.frouter, mevent.event)

    def setting(self, opt, val):
        stype = FS.fluid_settings_get_type(self.st, opt.encode())
        if stype == FLUID_STR_TYPE:
            FS.fluid_settings_setstr(self.st, opt.encode(), str(val).encode())
        elif stype == FLUID_INT_TYPE:
            FS.fluid_settings_setint(self.st, opt.encode(), int(val))
        elif stype == FLUID_NUM_TYPE:
            FS.fluid_settings_setnum(self.st, opt.encode(), c_double(val))

    def get_setting(self, opt):
        stype = FS.fluid_settings_get_type(self.st, opt.encode())
        if stype == FLUID_STR_TYPE:
            strval = create_string_buffer(32)
            if FS.fluid_settings_copystr(self.st, opt.encode(), strval, 32) == FLUID_OK:
                return strval.value.decode()
        elif stype == FLUID_INT_TYPE:
            val = c_int()
            if FS.fluid_settings_getint(self.st, opt.encode(), byref(val)) == FLUID_OK:
                return val.value
        elif stype == FLUID_NUM_TYPE:
            num = c_double()
            if FS.fluid_settings_getnum(self.st, opt.encode(), byref(num)) == FLUID_OK:
                return round(num.value, 6)
        return None

    def load_soundfont(self, sfont):
        i = FS.fluid_synth_sfload(self.fsynth, str(sfont).encode(), False)
        if i == FLUID_FAILED:
            return False
        self.sfid[sfont] = i
        return True

    def unload_soundfont(self, sfont):
        if FS.fluid_synth_sfunload(self.fsynth, self.sfid[sfont], False) == FLUID_FAILED:
            return False
        del self.sfid[sfont]
        return True

    def program_select(self, chan, sfont, bank, prog):
        if sfont not in self.sfid:
            return False
        x = FS.fluid_synth_program_select(self.fsynth, chan, self.sfid[sfont], bank, prog)
        if x == FLUID_FAILED:
            return False
        return True

    def program_unset(self, chan):
        FS.fluid_synth_unset_program(self.fsynth, chan)

    def program_info(self, chan):
        i = c_int()
        bank = c_int()
        prog = c_int()
        FS.fluid_synth_get_program(self.fsynth, chan, byref(i), byref(bank), byref(prog))
        if i.value not in self.sfid.values():
            return None
        sfont = {v: k for k, v in self.sfid.items()}[i.value]
        return sfont, bank.value, prog.value

    def send_event(self, type, chan, par1, par2=None):
        newevent = MidiEvent(FS.new_fluid_midi_event())
        newevent.type = type
        newevent.chan = chan
        newevent.par1 = par1
        newevent.par2 = par2
        self.custom_midi_router(None, newevent.event)

    def send_sysex(self, data):
        newevent = MidiEvent(FS.new_fluid_midi_event())
        syxdata = (c_int * len(data))(*data)
        FS.fluid_midi_event_set_sysex(newevent.event, syxdata, sizeof(syxdata), True)
        self.custom_midi_router(None, newevent.event)

    def send_cc(self, chan, ctrl, val):
        FS.fluid_synth_cc(self.fsynth, chan, ctrl, val)

    def get_cc(self, chan, ctrl):
        val = c_int()
        FS.fluid_synth_get_cc(self.fsynth, chan, ctrl, byref(val))
        return val.value

    def router_clear(self):
        FS.fluid_midi_router_clear_rules(self.frouter)
        self.xrules = []

    def router_default(self):
        FS.fluid_midi_router_set_default_rules(self.frouter)
        self.xrules = []

    def router_addrule(self, type, chan, par1, par2, **apars):
        if type[0] != type[-1]:
            self.xrules.insert(0, TransRule(type, chan, par1, par2))
        elif apars:
            self.xrules.insert(0, ExtRule(type, chan, par1, par2, **apars))
            if 'arpeggiator' in apars:
                self.xrules.insert(0, ExtRule(['noteoff'], chan, par1, (0, 127, 0, 0), **apars))
        elif type[0] in list(MIDI_TYPES)[:6]:
            rule = FS.new_fluid_midi_router_rule()
            if chan:
                FS.fluid_midi_router_rule_set_chan(rule, *Route(*chan))
            if par1:
                FS.fluid_midi_router_rule_set_param1(rule, *Route(*par1))
            if par2:
                FS.fluid_midi_router_rule_set_param2(rule, *Route(*par2))
            FS.fluid_midi_router_add_rule(self.frouter, rule, list(MIDI_TYPES).index(type[0]))

    def players_clear(self, save=[]):
        for name in set(self.players) - set(save):
            self.players[name].dismiss()
            del self.players[name]

    def sequencer_add(self, name, notes, tdiv=8, swing=0.5, groove=1, tempo=120):
        if name not in self.players:
            self.players[name] = Sequencer(self, notes, tdiv, swing, groove)
            self.players[name].set_tempo(tempo)

    def arpeggiator_add(self, name, tdiv=8, swing=0.5, style='', octaves=1, groove=1, tempo=120):
        if name not in self.players:
            self.players[name] = Arpeggiator(self, tdiv, swing, groove, style, octaves)
            self.players[name].set_tempo(tempo)

    def midiplayer_add(self, name, file, loops=[], barlength=1, chan=None, mask=[], tempo=0):
        if name not in self.players:
            self.players[name] = MidiPlayer(self, file, loops, barlength, chan, mask)
            if tempo > 0:
                self.players[name].set_tempo(tempo)

    def get_sfpresets(self, sfont):
        presets = []
        sfont_obj = FS.fluid_synth_get_sfont_by_id(self.fsynth, self.sfid[sfont])
        FS.fluid_sfont_iteration_start(sfont_obj)
        while True:
            p = FS.fluid_sfont_iteration_next(sfont_obj)
            if p == None: break
            presets.append(PresetInfo(p))
        return presets

    if LADSPA_SUPPORT:
        def fxchain_clear(self, save=[]):
            clear = set(self.ladspafx) - set(save)
            if clear:
                FS.fluid_ladspa_reset(self.ladspa)
                for name in clear:
                    del self.ladspafx[name]
                for ladpsafx in self.ladspafx.values():
                    ladpsafx.fxunits = []

        def fxchain_add(self, name, lib, plugin=None, chan=None, audio='stereo', vals={}):
            if name not in self.ladspafx:
                if FS.fluid_ladspa_is_active(self.ladspa):
                    FS.fluid_ladspa_reset(self.ladspa)
                self.ladspafx[name] = LadspaEffect(self, name, lib, plugin, chan, audio)
            self.ladspafx[name].portvals.update(vals)

        def fxchain_connect(self):
            if self.ladspafx == {} or FS.fluid_ladspa_is_active(self.ladspa): return
            for effect in self.ladspafx.values():
                effect.addfxunits()
                for ctrl, val in effect.portvals.items():
                    effect.setcontrol(ctrl, val)
            b = -1
            for midichannels, hostports, outports in self.port_mapping:
                effects = [e for e in self.ladspafx.values() if hostports in e.links]
                if not effects: continue
                lastports = hostports
                for effect in effects[0:-1]:
                    b += 2
                    buffers = (f"buffer{b}", f"buffer{b + 1}")
                    FS.fluid_ladspa_add_buffer(self.ladspa, buffers[0].encode())
                    FS.fluid_ladspa_add_buffer(self.ladspa, buffers[1].encode())
                    effect.link(hostports, lastports, buffers)
                    lastports = buffers
                effects[-1].link(hostports, lastports, outports)
            FS.fluid_ladspa_activate(self.ladspa)
    else:
        def fxchain_clear(self):
            pass

        def fxchain_add(self, name, lib, plugin=None, chan=None, audio='stereo', vals={}):
            pass

        def fxchain_connect(self):
            pass
