"""ctypes bindings and interface classes for fluidsynth
"""
from ctypes.util import find_library
from ctypes import *

FLUID_OK = 0
FLUID_FAILED = -1
FLUID_NUM_TYPE = 0
FLUID_INT_TYPE = 1
FLUID_STR_TYPE = 2
FLUID_SEQ_TIMER = 17
FLUID_SEQ_UNREGISTERING = 21
FLUID_PLAYER_TEMPO_INTERNAL = 0
FLUID_PLAYER_TEMPO_EXTERNAL_MIDI = 2
FLUID_PLAYER_PLAYING = 1
FLUID_PLAYER_DONE = 3
RULE_TYPES = 'note', 'cc', 'prog', 'pbend', 'cpress', 'kpress'
MIDI_TYPES = {'noteoff': 0x80, 'note': 0x90, 'kpress': 0xa0, 'cc': 0xb0,
    'prog': 0xc0, 'cpress': 0xd0, 'pbend': 0xe0, 'sysex': 0xf0,
    'clock': 0xf8, 'start': 0xfa, 'continue': 0xfb, 'stop': 0xfc}
SEQ_LAG = 10

fslib = find_library('fluidsynth') or find_library('libfluidsynth-3')
if fslib is None:
    raise ImportError("Couldn't find the FluidSynth library.")
FS = CDLL(fslib)
ladspa_available = hasattr(FS, 'fluid_ladspa_reset')

# type hints for ctypes as needed
FS.new_fluid_midi_event.restype = c_void_p
FS.new_fluid_event.restype = c_void_p
FS.fluid_preset_get_name.restype = c_char_p
FS.fluid_sfont_iteration_next.restype = c_void_p
FS.fluid_synth_handle_midi_event.argtypes = c_void_p, c_void_p
FS.fluid_midi_router_handle_midi_event.argtypes = c_void_p, c_void_p
fl_eventcallback = CFUNCTYPE(c_int, c_void_p, c_void_p)


class FluidMidiEvent:

    def __init__(self, e):
        b = FS.fluid_midi_event_get_type(c_void_p(e))
        self.type = {v: k for k, v in MIDI_TYPES.items()}.get(b)
        if self.type == 'noteoff':
            self.type = 'note'
            self.chan = FS.fluid_midi_event_get_channel(c_void_p(e)) + 1
            self.num = FS.fluid_midi_event_get_control(c_void_p(e))
            self.val = 0
        elif self.type in ('note', 'kpress', 'cc'):
            self.chan = FS.fluid_midi_event_get_channel(c_void_p(e)) + 1
            self.num = FS.fluid_midi_event_get_control(c_void_p(e))
            self.val = FS.fluid_midi_event_get_value(c_void_p(e))
        elif self.type in ('prog', 'cpress', 'pbend'):
            self.chan = FS.fluid_midi_event_get_channel(c_void_p(e)) + 1
            self.val = FS.fluid_midi_event_get_control(c_void_p(e))

    def __repr__(self):
        return ', '.join([f'{k}={v}' for k, v in self.__dict__.items()])


class SeqClient:

    def __init__(self, synth):
        self.synth = synth
        self.callback = CFUNCTYPE(None, c_uint, c_void_p, c_void_p, c_void_p)(
                lambda _, __, ___, ____: self.scheduler())
        self.id = FS.fluid_sequencer_register_client(synth.fseq, b'', self.callback, None)
        self.ticksperbeat = 500 # default 120bpm at 1000 ticks/sec
        self.pos = 0
        self.playing = False

    def set_tempo(self, bpm):
        # default fluid_sequencer time scale is 1000 ticks per second
        self.ticksperbeat = 1000 * 60 / bpm

    def set_swing(self, swing):
        swing = min(max(0.5, swing), 0.99)
        if self.tdiv >= 8 and self.tdiv % 3:
            self.swing = [2 * swing, 2  - 2 * swing]
        else:
            self.swing = [1, 1]

    def set_groove(self, groove):
        if not isinstance(groove, list):
            groove = [groove, 1]
        self.groove = [g/max(groove) for g in groove]

    def dismiss(self):
        self.playing = False
        FS.fluid_sequencer_remove_events(
                c_void_p(self.synth.fseq), c_short(-1),
                c_short(self.id), FLUID_SEQ_TIMER)
        FS.fluid_sequencer_unregister_client(self.synth.fseq, self.id)


class Sequence(SeqClient):

    def __init__(self, synth, seq):
        super().__init__(synth)
        self.events = getattr(seq, 'events')
        self.order = getattr(seq, 'order', [1])
        self.tdiv = getattr(seq, 'tdiv', 8)
        self.set_swing(getattr(seq, 'swing', 0.5))
        self.set_groove(getattr(seq, 'groove', 1))

    def scheduler(self):
        if not self.playing:
            return
        if not self.events:
            return
        accent = self.groove[self.step % len(self.groove)]
        pattern = self.events[self.order[self.pos] - 1]
        for track in pattern:
            event = track[self.step % len(track)]
            if isinstance(event, str):
                continue
            if event.type == 'note':
                self.synth.schedule_event(event.copy(val=event.val * accent), self.id, self.nexttick)
                dur = 0
                for i in range(len(track) - 1):
                    dur += self.swing[(self.step + i) % 2] * self.ticksperbeat * 4 / self.tdiv
                    if track[(self.step + i + 1) % len(track)] != '+':
                        break
                self.synth.schedule_event(event.copy(val=0), self.id, self.nexttick + dur)
            else:
                self.synth.schedule_event(event, self.id, self.nexttick)
        dur = self.swing[self.step % 2] * self.ticksperbeat * 4 / self.tdiv
        self.step += 1
        if self.step == max([len(track) for track in pattern]):
            self.pos = self.next
            self.step = 0
            self.next = (self.pos + 1) % len(self.order)
            if self.order[self.next] < 0:
                self.next += self.order[self.next]
        if self.order[self.pos] == 0:
            self.play(0)
        else:
            self.synth.schedule_callback(self.id, self.nexttick + dur - SEQ_LAG)
            self.nexttick += dur

    def play(self, pos=-1):
        if self.playing:
            if pos == 0:
                self.playing = False
                FS.fluid_sequencer_remove_events(
                        c_void_p(self.synth.fseq), c_short(-1),
                        c_short(self.id), FLUID_SEQ_TIMER)
            elif pos > 0:
                self.next = (pos - 1) % len(self.order)
        else:
            if pos > 0:
                self.pos = (pos - 1) % len(self.order)                    
            elif self.order[self.pos] == 0:
                self.pos = (self.pos + 1) % len(self.order)
            self.next = (self.pos + 1) % len(self.order)
            if self.order[self.next] < 0:
                self.next += self.order[self.next]
            self.step = 0
            self.nexttick = self.synth.currenttick
            self.playing = True
            self.scheduler()


class Arpeggio(SeqClient):

    def __init__(self, synth, arp):
        super().__init__(synth)
        self.style = getattr(arp, 'style')
        self.tdiv = getattr(arp, 'tdiv', 8)
        self.set_swing(getattr(arp, 'swing', 0.5))
        self.set_groove(getattr(arp, 'groove', 1))
        self.keysdown = set()
        self.step = 0

    def scheduler(self):
        if not self.playing:
            return
        dur = self.swing[self.step % 2] * self.ticksperbeat * 4 / self.tdiv
        accent = self.groove[self.step % len(self.groove)]
        for event in self.notes[self.step % len(self.notes)]:
            self.synth.schedule_event(event.copy(val=event.val * accent), self.id, self.nexttick)
            self.synth.schedule_event(event.copy(val=0), self.id, self.nexttick + dur)
        self.step += 1
        self.synth.schedule_callback(self.id, self.nexttick + dur - SEQ_LAG)
        self.nexttick += dur

    def add(self, note):
        if note.val > 0:
            self.keysdown.add(note)
            nd = len(self.keysdown)
        else:
            for k in self.keysdown:
                if k.chan == note.chan and k.num == note.num:
                    self.keysdown.remove(k)
                    break
            nd = -len(self.keysdown)
        notes = list(self.keysdown)
        if self.style in ('up', 'down', 'both'):
            notes.sort(key=lambda n: n.num)
        if self.style == 'down':
            notes.reverse()
        elif self.style == 'both':
            notes += notes[-2:0:-1]
        if self.style == 'chord':
            self.notes = [notes]
            if self.step == 1:
                self.nexttick = self.synth.currenttick
                dur = self.swing[0] * self.ticksperbeat * 4 / self.tdiv
                accent = self.groove[0]
                self.synth.schedule_event(note.copy(val=note.val * accent), self.id, self.nexttick)
                self.synth.schedule_event(note.copy(val=0), self.id, self.nexttick + dur)
                self.nexttick += dur
        else:
            self.notes = [[n] for n in notes]
        if nd == 1:
            if not self.playing:
                self.step = 0
                self.nexttick = self.synth.currenttick
                self.playing = True
                self.scheduler()
        elif nd == 0:
            self.playing = False
            FS.fluid_sequencer_remove_events(
                    c_void_p(self.synth.fseq), c_short(-1),
                    c_short(self.id), FLUID_SEQ_TIMER)


class MidiLoop(SeqClient):

    def __init__(self, synth, loop):
        super().__init__(synth)
        self.beats = getattr(loop, 'beats')
        self.fixedbeats = bool(self.beats)
        self.recording = False
        self.events = []
        self.layers = [[]]

    def scheduler(self):
        if not self.playing:
            return
        if self.pos < 0:
            self.starttick += self.beats * self.ticksperbeat
            self.events = [event for layer in self.layers for event in layer]
            self.events.sort(key=lambda e: e[0])
            self.pos = 0
        if self.events[self.pos:]:
            b, event = self.events[self.pos]
            t = self.starttick + b * self.ticksperbeat
            self.synth.schedule_event(event, self.id, t)
            self.pos += 1
        if self.events[self.pos:]:
            t = self.starttick + self.events[self.pos][0] * self.ticksperbeat
            self.synth.schedule_callback(self.id, t - SEQ_LAG)            
        else:
            self.pos = -1
            nextloop = self.starttick + self.beats * self.ticksperbeat
            self.synth.schedule_callback(self.id, nextloop)

    def play(self, p=1):
        self.playing = p
        if p:
            self.starttick = self.synth.currenttick
            self.events = [event for layer in self.layers for event in layer]
            self.events.sort(key=lambda e: e[0])
            if self.beats:
                self.pos = 0
                self.scheduler()
        else:
            if self.recording:
                self.record(0)
            FS.fluid_sequencer_remove_events(
                    c_void_p(self.synth.fseq), c_short(-1),
                    c_short(self.id), FLUID_SEQ_TIMER)

    def record(self, r=1):
        if r >= 0:
            if self.recording:
                if self.layers[-1]:
                    self.layers.append([])
                if self.beats == 0:
                    self.beats = (self.synth.currenttick - self.starttick) / self.ticksperbeat
                    self.play()
            self.recording = r
        else:
            if self.layers[-1] == []:
                r -= 1
            self.layers = self.layers[:int(r)] + [[]]
            self.events = [event for layer in self.layers for event in layer]
            self.events.sort(key=lambda e: e[0])
            if not self.events:
                self.play(0)
                if not self.fixedbeats:
                    self.beats = 0
            elif self.playing:
                dt = self.synth.currenttick - self.starttick
                self.pos = 0
                for event in self.events:
                    if event[0] * self.ticksperbeat > dt:
                        break
                    self.pos += 1        

    def add(self, event):
        if not self.recording:
            return
        if not self.playing:
            self.play()
        b = (self.synth.currenttick - self.starttick) / self.ticksperbeat
        self.layers[-1].append((b, event))

    def set_tempo(self, bpm):
        ticksperbeat = 1000 * 60 / bpm
        if self.playing:
            t = self.synth.currenttick
            self.starttick = t - (t - self.starttick) * ticksperbeat / self.ticksperbeat
        self.ticksperbeat = ticksperbeat


class MidiFile:

    def __init__(self, synth, mfile):
        self.fplayer = FS.new_fluid_player(synth.fsynth)
        FS.fluid_player_add(self.fplayer, str(mfile.file).encode())
        self.jumps = getattr(mfile, 'jumps', [])
        self.barlength = getattr(mfile, 'barlength', 1)
        self.lasttick = 0
        self.seektick = None
        if getattr(mfile, 'route', 0):
            # route events directly to the fluidsynth router (default)
            self.frouter_handler = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
            frouter = FS.new_fluid_midi_router(synth.st, self.frouter_handler, synth.frouter)
        else:
            # apply custom routing and callbacks to all events (experimental)
            self.frouter_handler = fl_eventcallback(FS.fluid_synth_handle_midi_event)
            frouter = FS.new_fluid_midi_router(synth.st, self.frouter_handler, synth.fsynth)
        FS.fluid_midi_router_clear_rules(frouter)
        for rtype in set(RULE_TYPES) - set(getattr(mfile, 'mask', [])):
            rule = FS.new_fluid_midi_router_rule()
            if hasattr(mfile, 'shift'):
                FS.fluid_midi_router_rule_set_chan(rule, 0, 15, c_float(1), mfile.shift)
            FS.fluid_midi_router_add_rule(frouter, rule, RULE_TYPES.index(rtype))
        self.playback_callback = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
        FS.fluid_player_set_playback_callback(self.fplayer, self.playback_callback, frouter)
        self.tickcallback = CFUNCTYPE(None, c_void_p, c_uint)(lambda _, t: self.direct(t))
        FS.fluid_player_set_tick_callback(self.fplayer, self.tickcallback, None)
        FS.fluid_player_seek(self.fplayer, 0) # prevent skipping first note due to ?bug

    def play(self, pos=-1):
        if FS.fluid_player_get_status(self.fplayer) != FLUID_PLAYER_PLAYING:
            if pos > 0:
                seektick = int((pos - 1) * self.barlength)
                FS.fluid_player_seek(self.fplayer, seektick)
                self.lasttick = seektick
            FS.fluid_player_play(self.fplayer)
        elif pos > 0:
            self.seektick = int((pos - 1) * self.barlength)
        elif pos == 0:
            self.seektick = None
            FS.fluid_player_stop(self.fplayer)

    def direct(self, tick):
        if self.seektick != None:
            if tick % self.barlength < (tick - self.lasttick):
                FS.fluid_player_seek(self.fplayer, self.seektick)
                self.lasttick = self.seektick
                self.seektick = None
        elif self.lasttick < tick:
            for frombar, tobar in self.jumps:
                if self.lasttick < frombar * self.barlength <= tick:
                    totick = int((tobar - 1) * self.barlength)
                    if tobar == 0:
                        self.play(0)
                        totick = 0
                    FS.fluid_player_seek(self.fplayer, totick)
                    self.lasttick = totick
                    break
            else:
                self.lasttick = tick

    def set_tempo(self, bpm=0):
        if bpm:
            usec = int(60000000.0 / bpm) # usec per quarter note (MIDI standard)
            FS.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_EXTERNAL_MIDI, c_double(usec))
        else:
            FS.fluid_player_set_tempo(self.fplayer, FLUID_PLAYER_TEMPO_INTERNAL, c_double(1.0))

    def dismiss(self):
        FS.fluid_player_stop(self.fplayer)
        FS.delete_fluid_player(self.fplayer)


class LadspaEffect:
    
    def __init__(self, synth, name, fx):
        self.ladspa = synth.ladspa
        lib = str(fx.lib).encode()
        plugin = getattr(fx, 'plugin', '').encode() or None
        chan = getattr(fx, 'chan', [])
        audio = getattr(fx, 'audio', ('Input', 'Output'))
        portvals = getattr(fx, 'vals', {})
        groups = set([(n - 1) % len(synth.port_mapping) for n in chan])
        aports = [port.encode() for port in audio]
        stereo = True if len(aports) == 4 else False
        self.fxunits = []
        self.links = {}
        def addfxunit():
            fxunit = f"{name}{len(self.fxunits)}".encode()
            if FS.fluid_ladspa_add_effect(self.ladspa, fxunit, lib, plugin) != FLUID_OK:
                return False
            if FS.fluid_ladspa_effect_can_mix(self.ladspa, fxunit):
                FS.fluid_ladspa_effect_set_mix(self.ladspa, fxunit, 1, c_float(1.0))
            for port, val in portvals.items():
                FS.fluid_ladspa_effect_set_control(self.ladspa, fxunit, port.encode(), c_float(val))
            self.fxunits.append(fxunit)
            return True
        for group, (hostports, outports) in enumerate(synth.port_mapping):
            if groups and group not in groups:
                continue
            if stereo:
                if addfxunit():
                    self.links[hostports] = self.fxunits[-1:] * 2, aports[0:2], aports[2:4]
            else:
                if addfxunit() and addfxunit():
                    self.links[hostports] = self.fxunits[-2:], aports[0:1] * 2, aports[1:2] * 2

    def link(self, hostports, inputs, outputs):
        for fxunit, fxin, fxout, inp, outp in zip(*self.links[hostports], inputs, outputs):
            FS.fluid_ladspa_effect_link(self.ladspa, fxunit, fxin, inp.encode())
            FS.fluid_ladspa_effect_link(self.ladspa, fxunit, fxout, outp.encode())

    def setcontrol(self, port, val):
        for fxunit in self.fxunits:
            FS.fluid_ladspa_effect_set_control(self.ladspa, fxunit, port.encode(), c_float(val))


class SoundFont:

    def __init__(self, fsfont, id):
        self.id = id
        self._presets = {}
        FS.fluid_sfont_iteration_start(fsfont)
        while True:
            p = FS.fluid_sfont_iteration_next(fsfont)
            if p == None: break
            bank = FS.fluid_preset_get_banknum(p)
            prog = FS.fluid_preset_get_num(p)
            name = FS.fluid_preset_get_name(p).decode()
            self._presets[bank, prog] = name

    def __getitem__(self, p):
        return self._presets[p] if p in self._presets else ""

    def index(self, p):
        return list(self._presets).index(p)

    def __iter__(self):
        return iter(self._presets)


class Synth:

    def __init__(self, midi_handler=None, **fluidsettings):
        self.st = FS.new_fluid_settings()
        for name, val in fluidsettings.items():
            self[name] = val
        self.fsynth = FS.new_fluid_synth(self.st)
        FS.new_fluid_audio_driver(self.st, self.fsynth)
        self.frouter_handler = fl_eventcallback(FS.fluid_synth_handle_midi_event)
        self.frouter = FS.new_fluid_midi_router(self.st, self.frouter_handler, self.fsynth)
        if midi_handler:
            self.fdriver_handler = fl_eventcallback(
                lambda _, e: midi_handler(FluidMidiEvent(e)) or FLUID_OK
            )
        else:
            self.fdriver_handler = fl_eventcallback(FS.fluid_midi_router_handle_midi_event)
        FS.new_fluid_midi_driver(self.st, self.fdriver_handler, self.frouter)
        self.fseq = FS.new_fluid_sequencer2(0)
        self.id = FS.fluid_sequencer_register_fluidsynth(self.fseq, self.fsynth)
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
            FS.fluid_settings_setnum(self.st, name.encode(), c_double(float(val)))

    def load_soundfont(self, file):
        id = FS.fluid_synth_sfload(self.fsynth, str(file).encode(), False)
        if id == FLUID_FAILED:
            raise OSError(f"Unable to load {file}")
        fsfont = FS.fluid_synth_get_sfont_by_id(self.fsynth, id)
        return SoundFont(fsfont, id)

    def unload_soundfont(self, sfont):
        FS.fluid_synth_sfunload(self.fsynth, sfont.id, False)

    def program_select(self, chan, sfont, bank, prog):
        x = FS.fluid_synth_program_select(self.fsynth, chan - 1, sfont.id, bank, prog)
        return True if x == FLUID_OK else False

    def program_unset(self, chan):
        FS.fluid_synth_unset_program(self.fsynth, chan - 1)

    def program_info(self, chan):
        i = c_int()
        bank = c_int()
        prog = c_int()
        FS.fluid_synth_get_program(self.fsynth, chan - 1, byref(i), byref(bank), byref(prog))
        return i.value, bank.value, prog.value

    def get_cc(self, chan, ctrl):
        val = c_int()
        FS.fluid_synth_get_cc(self.fsynth, chan - 1, ctrl, byref(val))
        return val.value

    def router_clear(self):
        FS.fluid_midi_router_clear_rules(self.frouter)

    def router_default(self):
        FS.fluid_midi_router_set_default_rules(self.frouter)

    def router_addrule(self, rule):
        frule = FS.new_fluid_midi_router_rule()
        if chan := getattr(rule, 'chan', None):
            FS.fluid_midi_router_rule_set_chan(
                    frule, int(chan.min - 1), int(chan.max - 1),
                    c_float(chan.mul), int(chan.add + chan.mul - 1))
        if rule.type in ('prog', 'cpress', 'pbend'):
            if val := getattr(rule, 'val', None):
                FS.fluid_midi_router_rule_set_param1(
                        frule, int(val.min), int(val.max),
                        c_float(val.mul), int(val.add))
        else:
            if num := getattr(rule, 'num', None):
                FS.fluid_midi_router_rule_set_param1(
                        frule, int(num.min), int(num.max),
                        c_float(num.mul), int(num.add))
            if val := getattr(rule, 'val', None):
                FS.fluid_midi_router_rule_set_param2(
                        frule, int(val.min), int(val.max),
                        c_float(val.mul), int(val.add))
        FS.fluid_midi_router_add_rule(self.frouter, frule, RULE_TYPES.index(rule.type))

    def send_event(self, event, route=True):
        fmevent = FS.new_fluid_midi_event()
        if event.type == 'sysex':
            syxdata = (c_int * len(event.val))(*event.val)
            FS.fluid_midi_event_set_sysex(c_void_p(fmevent), syxdata, sizeof(syxdata), True)
        else:
            FS.fluid_midi_event_set_type(c_void_p(fmevent), MIDI_TYPES.get(event.type))
            if event.type in ('prog', 'cpress', 'pbend'):
                FS.fluid_midi_event_set_channel(c_void_p(fmevent), int(event.chan - 1))
                FS.fluid_midi_event_set_control(c_void_p(fmevent), int(event.val))
            elif event.type in ('note', 'kpress', 'cc'):
                FS.fluid_midi_event_set_channel(c_void_p(fmevent), int(event.chan - 1))
                FS.fluid_midi_event_set_control(c_void_p(fmevent), int(event.num))
                FS.fluid_midi_event_set_value(c_void_p(fmevent), int(event.val))
        if route:
            FS.fluid_midi_router_handle_midi_event(self.frouter, fmevent)
        else:
            FS.fluid_synth_handle_midi_event(self.fsynth, fmevent)

    def schedule_event(self, event, id=-1, time=None):
        if not hasattr(event, 'chan'):
            return
        fevent = FS.new_fluid_event()
        FS.fluid_event_set_source(c_void_p(fevent), c_short(id))
        FS.fluid_event_set_dest(c_void_p(fevent), c_short(self.id))
        chan, val = int(event.chan - 1), int(event.val)
        if event.type in ('note', 'cc', 'kpress'):
            num = int(event.num)
        if event.type == 'note':
            FS.fluid_event_noteon(c_void_p(fevent), chan, num, val)
        elif event.type == 'cc':
            FS.fluid_event_control_change(c_void_p(fevent), chan, num, val)
        elif event.type == 'prog':
            FS.fluid_event_program_change(c_void_p(fevent), chan, val)
        elif event.type == 'pbend':
            FS.fluid_event_pitch_bend(c_void_p(fevent), chan, val)
        elif event.type == 'cpress':
            FS.fluid_event_channel_pressure(c_void_p(fevent), chan, val)
        elif event.type == 'kpress':
            FS.fluid_event_key_pressure(c_void_p(fevent), chan, num, val)
        if time == None:
            time = self.currenttick
        FS.fluid_sequencer_send_at(
                c_void_p(self.fseq), c_void_p(fevent),
                c_uint(int(time)), 1)
        FS.delete_fluid_event(c_void_p(fevent))

    def schedule_callback(self, id, time):
        cb = FS.new_fluid_event()
        FS.fluid_event_set_source(c_void_p(cb), c_short(-1))
        FS.fluid_event_set_dest(c_void_p(cb), c_short(id))
        FS.fluid_event_timer(c_void_p(cb), c_void_p())
        FS.fluid_sequencer_send_at(
                c_void_p(self.fseq), c_void_p(cb),
                c_uint(int(time)), 1)
        FS.delete_fluid_event(c_void_p(cb))

    def player_remove(self, name):
        self.players[name].dismiss()
        del self.players[name]
    
    def sequence_add(self, name, seq):
        if name not in self.players:
            self.players[name] = Sequence(self, seq)
            self.players[name].set_tempo(getattr(seq, 'tempo', 120))

    def arpeggio_add(self, name, arp):
        if name not in self.players:
            self.players[name] = Arpeggio(self, arp)
            self.players[name].set_tempo(getattr(arp, 'tempo', 120))

    def midiloop_add(self, name, loop):
        if name not in self.players:
            self.players[name] = MidiLoop(self, loop)
            self.players[name].set_tempo(getattr(loop, 'tempo', 120))

    def midifile_add(self, name, mfile):
        if name not in self.players:
            self.players[name] = MidiFile(self, mfile)
            if hasattr(mfile, 'tempo'):
                self.players[name].set_tempo(mfile.tempo)

    def fxchain_clear(self):
        FS.fluid_ladspa_reset(self.ladspa)
        self.ladspafx = {}

    def fxchain_add(self, name, fx):
        if name not in self.ladspafx:
            self.ladspafx[name] = LadspaEffect(self, name, fx)

    def fxchain_connect(self):
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
        def fxchain_add(self, _, __): pass
        def fxchain_connect(self): pass

