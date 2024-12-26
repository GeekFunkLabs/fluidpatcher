"""ctypes bindings and interface classes for fluidsynth
"""
from ctypes.util import find_library
from ctypes import *

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
RULE_TYPES = 'note', 'cc', 'prog', 'pbend', 'cpress', 'kpress'
MIDI_TYPES = {'noteoff': 0x80, 'note': 0x90, 'kpress': 0xa0, 'cc': 0xb0, 'prog': 0xc0, 'cpress': 0xd0, 'pbend': 0xe0, 
              'sysex': 0xf0, 'clock': 0xf8, 'start': 0xfa, 'continue': 0xfb, 'stop': 0xfc}
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
specfunc(FS.fluid_synth_get_cc, c_int, c_void_p, c_int, c_int, POINTER(c_int))
def fl_synth_program_select(synth, chan, id, bank, prog):
    FS.fluid_synth_program_select(synth, chan - 1, id, bank, prog)
def fl_synth_unset_program(synth, chan):
    FS.fluid_synth_unset_program(synth, chan - 1)
def fl_synth_get_program(synth, chan, id, bank, prog):
    FS.fluid_synth_get_program(synth, chan - 1, id, bank, prog)
def fl_synth_get_cc(synth, chan, ctrl, val):
    FS.fluid_synth_get_cc(synth, chan - 1, ctrl, val)

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
def fl_midi_router_rule_set_chan(rule, min, max, mul, add):
    FS.fluid_midi_router_rule_set_chan(rule, int(min - 1), int(max - 1), mul, int(mul + add - 1))
def fl_midi_router_rule_set_param1(rule, min, max, mul, add):
    FS.fluid_midi_router_rule_set_param1(rule, int(min), int(max), mul, int(add))
def fl_midi_router_rule_set_param2(rule, min, max, mul, add):
    FS.fluid_midi_router_rule_set_param2(rule, int(min), int(max), mul, int(add))

# midi events
specfunc(FS.new_fluid_midi_event, c_void_p)
specfunc(FS.delete_fluid_event, None, c_void_p)
specfunc(FS.fluid_midi_event_get_type, c_int, c_void_p)
specfunc(FS.fluid_midi_event_set_type, c_int, c_void_p, c_int)
fl_midi_event_get_par1 = specfunc(FS.fluid_midi_event_get_key, c_int, c_void_p)
fl_midi_event_set_par1 = specfunc(FS.fluid_midi_event_set_key, c_int, c_void_p, c_int)
fl_midi_event_get_par2 = specfunc(FS.fluid_midi_event_get_velocity, c_int, c_void_p)
fl_midi_event_set_par2 = specfunc(FS.fluid_midi_event_set_velocity, c_int, c_void_p, c_int)
specfunc(FS.fluid_midi_event_get_channel, c_int, c_void_p)
specfunc(FS.fluid_midi_event_set_channel, c_int, c_void_p, c_int)
def fl_midi_event_get_channel(event):
    return FS.fluid_midi_event_get_channel(event) + 1
def fl_midi_event_set_channel(event, chan):
    FS.fluid_midi_event_set_channel(event, chan - 1)

# sequencer events
specfunc(FS.new_fluid_event, c_void_p)
specfunc(FS.delete_fluid_event, None, c_void_p)
specfunc(FS.fluid_event_noteon, None, c_void_p, c_int, c_int, c_int)
specfunc(FS.fluid_event_noteoff, None, c_void_p, c_int, c_int)
specfunc(FS.fluid_event_set_source, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_set_dest, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_timer, None, c_void_p, c_void_p)
specfunc(FS.fluid_event_get_type, c_int, c_void_p)
def fl_event_noteon(event, chan, key, vel):
    FS.fluid_event_noteon(event, chan - 1, key, vel)
def fl_event_noteoff(event, chan, key):
    FS.fluid_event_noteoff(event, chan - 1, key)

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

# ladspa effects
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
    ladspa_available = True
except AttributeError:
    ladspa_available = False


class FluidMidiEvent:

    def __init__(self, event):
		b = FS.fluid_midi_event_get_type(event)
		self.type = {v: k for k, v in MIDI_TYPES.items()}.get(b, None)
		self.chan = fl_midi_event_get_channel(event)
		if type in ('prog', 'cpress', 'pbend'):
			self.val = fl_midi_event_get_par1(event)
			self.num = None
		elif type in ('noteoff', 'note', 'kpress', 'cc'):
			self.num = fl_midi_event_get_par1(event)
			self.val = fl_midi_event_get_par2(event)


class SequencerNote:

    def __init__(self, chan, key, vel):
        self.chan = chan
        self.key = key
        self.vel = vel
        
    def __iter__(self):
        return iter([self])

    def schedule(self, seq, timeon, timeoff, accent=1):
        evt = FS.new_fluid_event()
        FS.fluid_event_set_source(evt, -1)
        FS.fluid_event_set_dest(evt, seq.fsynth_id)
        fl_event_noteon(evt, self.chan, self.key, int(min(self.vel * accent, 127)))
        FS.fluid_sequencer_send_at(seq.fseq, evt, int(timeon), 1)
        FS.delete_fluid_event(evt)
        evt = FS.new_fluid_event()
        FS.fluid_event_set_source(evt, -1)
        FS.fluid_event_set_dest(evt, seq.fsynth_id)
        fl_event_noteoff(evt, int(self.chan), int(self.key))
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

    def step(self, event, n):
        if n < 1:
            n = self.beat % len(self.notes)
        self.notes[n - 1] = SequencerNote(chan, key, vel)

    def scheduler(self, time=None, event=None, fseq=None, data=None):
        if event and FS.fluid_event_get_type(event) == FLUID_SEQ_UNREGISTERING:
            return
        if not self.notes: return
        dur = self.ticksperbeat * 4 / self.tdiv
        if self.tdiv >= 8 and self.tdiv % 3:
            if self.beat % 2: dur *= 2 * (1 - self.swing)
            else: dur *= 2 * self.swing
        pos = self.beat % len(self.notes)
        accent = self.groove[self.beat % len(self.groove)]
        for note in self.notes[pos]:
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
        FS.fluid_player_add(self.fplayer, str(file).encode())
        self.loops = list(zip(loops[::2], loops[1::2]))
        self.barlength = barlength
        self.seek = None
        self.seek_now = False
        self.lasttick = 0
        frouter = FS.new_fluid_midi_router(synth.st, fl_eventcallback(synth.custom_router), synth.frouter)
        FS.fluid_midi_router_clear_rules(frouter)
        for rtype in set(list(MIDI_TYPES)[:6]) - set(mask):
            rule = FS.new_fluid_midi_router_rule()
            if chan: fl_midi_router_rule_set_chan(rule, *chan)
            FS.fluid_midi_router_add_rule(frouter, rule, list(MIDI_TYPES).index(rtype))
        self.playback_callback = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
        FS.fluid_player_set_playback_callback(self.fplayer, self.playback_callback, frouter)
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
                if str(self.seek)[-1] in '+-':
                    inc = int(self.seek[-1] + self.seek[:-1])
                    self.seek = FS.fluid_player_get_current_tick(self.fplayer) + inc
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
    
    def __init__(self, synth, name, lib, plugin, group, audio):
        self.synth = synth
        self.name = name
        self.lib = str(lib).encode()
        self.plugin = plugin.encode() if plugin else None
        self.groups = group
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
        group = 0
        for hostports, outports in self.synth.port_mapping:
            group += 1
            if self.groups and group not in self.groups: continue
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


class Soundfont:

    def __init__(self, id):
        self.id = id
        self.presets = []
        fsfont = FS.fluid_synth_get_sfont_by_id(self.fsynth, id)
        FS.fluid_sfont_iteration_start(fsfont)
        while True:
            p = FS.fluid_sfont_iteration_next(fsfont)
            if p == None: break
            bank = FS.fluid_preset_get_banknum(p)
            prog = FS.fluid_preset_get_num(p)
            name = FS.fluid_preset_get_name(p).decode()
            self.presets.append((bank, prog, name))


class Synth:

    def __init__(self, midi_handler=None, **fluidsettings):
        self.st = FS.new_fluid_settings()
        for name, val in fluidsettings.items():
            self[name] = val
        self.fsynth = FS.new_fluid_synth(self.st)
        FS.new_fluid_audio_driver(self.st, self.fsynth)
        self.frouter = FS.new_fluid_midi_router(self.st, FS.fluid_synth_handle_midi_event, self.fsynth)
        if midi_handler:
            self.fdriver_callback = fl_eventcallback(lambda _, e: midi_handler(FluidMidiEvent(e)))
            FS.new_fluid_midi_driver(self.st, self.fdriver_callback, self.frouter)
        else:
            FS.new_fluid_midi_driver(self.st, FS.fluid_midi_router_handle_midi_event, self.frouter)
        self.midi_callback = None
        self.fseq = FS.new_fluid_sequencer2(0)
        self.fsynth_id = FS.fluid_sequencer_register_fluidsynth(self.fseq, self.fsynth)
        self.players = {}
		self.ladspafx = {}
        if ladspa_available:
            if self['synth.audio-groups'] == 1:
                hostports = outports = [('Main:L', 'Main:R')]
            else:
                hostports = [(f'Main:L{i}', f'Main:R{i}') for i in range(1, self['synth.audio-groups'] + 1)]
                outports = hostports[0:self['synth.audio-channels']] * self['synth.audio-groups']
            self.port_mapping = list(zip(hostports, outports))
            self.ladspa = FS.fluid_synth_get_ladspa_fx(self.fsynth)

    @property
    def currenttick(self):
        return FS.fluid_sequencer_get_tick(self.fseq)

    def reset(self):
        for name in self.players:
            self.player_remove(name)
        self.fxchain_clear()
        FS.fluid_synth_system_reset(self.fsynth)

    def __getitem__(self, name):
        stype = FS.fluid_settings_get_type(self.st, name.encode())
        if stype == FLUID_STR_TYPE:
            strval = create_string_buffer(32)
            if FS.fluid_settings_copystr(self.st, name.encode(), strval, 32) == FLUID_OK:
                return strval.value.decode()
        elif stype == FLUID_INT_TYPE:
            val = c_int()
            if FS.fluid_settings_getint(self.st, name.encode(), byref(val)) == FLUID_OK:
                return val.value
        elif stype == FLUID_NUM_TYPE:
            num = c_double()
            if FS.fluid_settings_getnum(self.st, name.encode(), byref(num)) == FLUID_OK:
                return round(num.value, 6)
        return None

    def __setitem__(self, name, val):
        stype = FS.fluid_settings_get_type(self.st, name.encode())
        if stype == FLUID_STR_TYPE:
            FS.fluid_settings_setstr(self.st, name.encode(), str(val).encode())
        elif stype == FLUID_INT_TYPE:
            FS.fluid_settings_setint(self.st, name.encode(), int(val))
        elif stype == FLUID_NUM_TYPE:
            FS.fluid_settings_setnum(self.st, name.encode(), c_double(val))

    def load_soundfont(self, file):
        id = FS.fluid_synth_sfload(self.fsynth, str(file).encode(), False)
        if id == FLUID_FAILED:
            raise OSError(f"Unable to load {file}")
        return SoundFont(id)

    def unload_soundfont(self, sfont):
        FS.fluid_synth_sfunload(self.fsynth, sfont.id, False)

    def program_select(self, chan, sfont, bank, prog):
        x = fl_synth_program_select(self.fsynth, chan, sfont.id, bank, prog)
        return True if x == FLUID_OK else False

    def program_unset(self, chan):
        fl_synth_unset_program(self.fsynth, chan)

    def program_info(self, chan):
        i = c_int()
        bank = c_int()
        prog = c_int()
        fl_synth_get_program(self.fsynth, chan, byref(i), byref(bank), byref(prog))
        return i.value, bank.value, prog.value

    def get_cc(self, chan, ctrl):
        val = c_int()
        fl_synth_get_cc(self.fsynth, chan, ctrl, byref(val))
        return val.value

    def router_clear(self):
        FS.fluid_midi_router_clear_rules(self.frouter)

    def router_default(self):
        FS.fluid_midi_router_set_default_rules(self.frouter)

    def router_addrule(self, type, chan=None, num=None, val=None):
		if type in RULE_TYPES:
            rule = FS.new_fluid_midi_router_rule()
            if chan:
				fl_midi_router_rule_set_chan(rule, *chan)
            if par1:
				fl_midi_router_rule_set_param1(rule, *par1)
            if par2:
				fl_midi_router_rule_set_param2(rule, *par2)
            FS.fluid_midi_router_add_rule(self.frouter, rule, RULE_TYPES.index(type))

    def send_event(self, event, route=True):
		fevent = FS.new_fluid_midi_event()
		if event.type == 'sysex':
			syxdata = (c_int * len(event.val))(*event.val)
			FS.fluid_midi_event_set_sysex(fevent, syxdata, sizeof(syxdata), True)
		else:
			FS.fluid_midi_event_set_type(fevent, MIDI_TYPES.get(event.type))
			if event.type in ('prog', 'cpress', 'pbend'):
				fl_midi_event_set_channel(fevent, event.chan)
				fl_midi_event_set_par1(fevent, event.val)
			elif event.type in ('noteoff', 'note', 'kpress', 'cc'):
				fl_midi_event_set_channel(fevent, event.chan)
				fl_midi_event_set_par1(fevent, event.num)
				fl_midi_event_set_par2(fevent, event.val)
        if route:
            FS.fluid_midi_router_handle_midi_event(self.frouter, fevent)
        else:
            FS.fluid_synth_handle_midi_event(self.fsynth, fevent)

    def player_remove(self, name):
        self.players[name].dismiss()
        del self.players[name]
    
    def sequencer_add(self, name, notes, tdiv=8, swing=0.5, groove=[1], tempo=120, **_):
        if name not in self.players:
            self.players[name] = Sequencer(self, notes, tdiv, swing, groove)
            self.players[name].set_tempo(tempo)

    def arpeggiator_add(self, name, tdiv=8, swing=0.5, groove=[1], style='', octaves=1, tempo=120, **_):
        if name not in self.players:
            self.players[name] = Arpeggiator(self, tdiv, swing, groove, style, octaves)
            self.players[name].set_tempo(tempo)

    def midiplayer_add(self, name, file, loops=[], barlength=1, chan=None, mask=[], tempo=0, **_):
        if name not in self.players:
            self.players[name] = MidiPlayer(self, file, loops, barlength, chan, mask)
            if tempo > 0:
                self.players[name].set_tempo(tempo)

    def fxchain_clear(self, save=[]):
        FS.fluid_ladspa_reset(self.ladspa)
        self.ladspafx = {}

    def fxchain_add(self, name, lib, plugin=None, group=[], audio='mono', vals={}, **_):
        if name not in self.ladspafx:
            self.ladspafx[name] = LadspaEffect(self, name, lib, plugin, group, audio)
            self.ladspafx[name].portvals.update(vals)

    def fxchain_connect(self):
        for effect in self.ladspafx.values():
            effect.addfxunits()
            for ctrl, val in effect.portvals.items():
                effect.setcontrol(ctrl, val)
        b = -1
        for hostports, outports in self.port_mapping:
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

    if not ladspa_available:
        def fxchain_clear(self): pass
        def fxchain_add(self, **_): pass
        def fxchain_connect(self): pass
