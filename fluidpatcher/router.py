MIDI_TYPES = {'noteoff': 0x8, 'note': 0x9, 'kpress': 0xa, 'cc': 0xb, 'prog': 0xc, 'cpress': 0xd, 'pbend': 0xe,
              'sysex': 0xf0, 'clock': 0xf8, 'start': 0xfa, 'continue': 0xfb, 'stop': 0xfc}


class MidiEvent:

    def __init__(self, event, **apars):
        self.__dict__.update(apars)
        self.type = event.type
        self.chan = event.chan
        self.num = event.num
        self.val = event.val
        
    def __repr__(self):
        return str(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)
    
    def tobytes(self):
        if self.type in MIDI_TYPES[:7]:
            b = [MIDI_TYPES[self.type] * 16 + self.channel - 1]
            if self.type == 'pbend':
                b += [(self.val + 8192) % 128, (self.val + 8192) // 128]
            elif self.type in ('prog', 'cpress'):
                b += [self.val]
            else:
                b += [self.num]
                b += [int(self.val)]
        else:
            b = [MIDI_TYPES[self.type]]
            if self.type == 'sysex':
                b += [*self.val, 247]
        return b


class Route:

    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add
            
    def __iter__(self):
        return iter([self.min, self.max, self.mul, self.add])


class FluidRule:

    def __init__(self, type, chan=None, num=None, val=None, tags=[]):
        self.type = type
        self.chan = Route(*chan) if chan else None
        self.num = Route(*num) if num else None
        self.val = Route(*val) if val else None
        self.tags = tags


class CustomRule:

    def __init__(self, types, chan=None, num=None, val=None, **pars):
        self.fromtype = types[0]
        self.totype = types[-1]
        self.chan = Route(*chan) if chan else None
        self.num = Route(*num) if num else None
        self.val = Route(*val) if val else None
        self.__dict__.update(pars)

    def __contains__(self, k):
        return k in self.__dict__

    def applies(self, event):
        if self.fromtype != event.type:
            return False
        for par in 'chan', 'num', 'val':
            if spec := getattr(self, par):
                epar = getattr(event, par)
                if spec.min > spec.max:
                    if spec.min < epar < spec.max:
                        return False
                else:
                    if not (spec.min <= epar <= spec.max):
                        return False
        return True

    def apply(self, event):
        newevent = MidiEvent(event, **self.pars)
        newevent.type = self.totype
        if self.fromtype in ('noteoff', 'note', 'kpress', 'cc', 'prog', 'cpress', 'pbend'):
            if self.chan != None:
                newevent.chan = round(event.chan * self.chan.mul + self.chan.add)
            if self.val != None:
                newevent.val = event.val * self.val.mul + self.val.add
            if self.totype in ('noteoff', 'note', 'kpress', 'cc'):
                if self.fromtype in ('noteoff', 'note', 'kpress', 'cc'):
                    newevent.num = round(event.num * self.num.mul + self.num.add)
                else:
                    newevent.num = self.num.min
        else:
            if self.chan != None:
                newevent.chan = self.chan.min
            if self.num != None:
                newevent.num = self.num.min
            if self.fromtype == 'clock':
                newevent.val = 0.041666664
            elif self.val != None:
                newevent.val = self.val.min
            elif self.fromtype in ('start', 'continue'):
                newevent.val = -1
            elif self.fromtype == 'stop':
                newevent.val = 0
        return newevent


class TransRule(CustomRule):

    def __init__(self, types, chan=None, num=None, val=None):
        super().__init__(types, chan, num, val, tags)


class Router:

    def __init__(self, fluid_default=True):
        self.synth = None
        self.rules = []
        self.fluid_default = fluid_default
        self.clocks = [0, 0]
        self.midi_callback = None

    def reset(self):
        self.rules = []
        self.synth.router_clear()
        if self.fluid_default:
            self.synth.router_default()

    def add(self, type, chan=None, num=None, val=None, **apars):
        if apars:
            self.rules.append(CustomRule(type, chan, num, val, tags, **apars))
        elif type[0] != type[1]:
            self.rules.append(TransRule(type, chan, num, val, tags))
        elif type[0] in ('note', 'kpress', 'cc', 'prog', 'cpress', 'pbend'):
            self.rules.append(FluidRule(type[0], chan, num, val, tags))
            self.synth.router_clear()
            if self.fluid_default:
                self.synth_router_default()
            for rule in self.rules[::-1]:
                if isinstance(rule, FluidRule):
                    self.synth.router_addrule(rule.type, rule.chan, rule.num, rule.val)

    def find(self, **pars):
        pass

    def handle_midi(self, event):
        t = self.synth.currenttick
        dt = 0
        for rule in list(self.customrules):
            if not rule.applies(event):
                continue
            newevent = rule.apply(event)
            if isinstance(rule, TransRule):
                self.synth.send_event(newevent, route=False)
            elif 'fluidsetting' in rule:
                 self.synth.setting(rule.fluidsetting, newevent.val)
            elif 'sequencer' in rule:
                if rule.sequencer in self.synth.players:
                    if 'step' in rule:
                        self.synth.players[rule.sequencer].step(res.event, rule.step) # should be rule.event? new event?
                    self.synth.players[rule.sequencer].play(newevent.val)
            elif 'arpeggiator' in rule:
                if rule.arpeggiator in self.synth.players:
                    self.synth.players[rule.arpeggiator].note(newevent.chan, newevent.num, newevent.val)
            elif 'midiplayer' in rule:
                if rule.midiplayer in self.synth.players:
                    if 'tick' in rule:
                        self.synth.players[rule.midiplayer].transport(newevent.val, rule.tick)
                    else:
                        self.synth.players[rule.midiplayer].transport(newevent.val)
            elif 'tempo' in rule:
                if rule.tempo in self.synth.players:
                    self.synth.players[rule.tempo].set_tempo(newevent.val)
            elif 'swing' in rule:
                if rule.swing in self.synth.players:
                    self.synth.players[rule.swing].swing = newevent.val
            elif 'groove' in rule:
                if rule.groove in self.synth.players:
                    self.synth.players[rule.groove].groove = [newevent.val]
            elif 'sync' in rule:
                if rule.sync in self.synth.players:
                    dt, dt2 = t - self.clocks[0], self.clocks[0] - self.clocks[1]
                    bpm = 1000 * 60 * newevent.val / dt
                    if dt2/dt > 0.5:
                        self.synth.players[rule.sync].set_tempo(bpm)
            elif 'ladspafx' in rule:
                if rule.ladspafx in self.synth.ladspafx:
                    self.synth.ladspafx[rule.ladspafx].setcontrol(rule.port, newevent.val)
            else:
                # not handled here, pass the MidiEvent to the callback
                if self.midi_callback:
                    self.midi_callback(newevent)
        if dt > 0:
            self.clocks = t, self.clocks[0]
        if self.midi_callback:
            # send the FluidEvent to the callback
            self.midi_callback(event)
        # pass the original event along to the fluid router
        self.synth.send_event(event)
