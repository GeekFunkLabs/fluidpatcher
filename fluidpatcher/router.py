class MidiEvent:

    def __init__(self, event, **apars):
        self.__dict__.update(apars)
        self.type = event.type
        self.chan = event.chan
        self.num = event.num
        self.val = event.val


class Route:

    def __init__(self, min, max, mul, add):
        self.min = min
        self.max = max
        self.mul = mul
        self.add = add
            
    def __iter__(self):
        return iter([self.min, self.max, self.mul, self.add])


class FluidRule:

    def __init__(self, type, chan=None, num=None, val=None):
        self.type = type[0]
        self.chan = Route(chan[0], chan[0], 0, chan[1]) if chan else None
        self.num = Route(*num) if num else None
        self.val = Route(*val) if val else None


class CustomRule:

    def __init__(self, types, chan=None, num=None, val=None, **pars):
        self.fromtype = types[0]
        self.totype = types[-1]
        self.chan = Route(chan[0], chan[0], 0, chan[1]) if chan else None
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
                if 'log' in self.pars:
                    tomin = self.val.min * self.val.mul + self.val.add
                    tomax = self.val.max * self.val.mul + self.val.add
                    x = (event.val - self.val.min) / (self.val.max - self.val.min)
                    newevent.val = tomin + (tomax - tomin) * (self.log ** x - 1) / (self.log - 1)
                else:
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


class Router:

    def __init__(self, fluid_default=True):
        self.fluid_default = fluid_default
        self.customrules = []
        self.fluidrules = []
        self.synth = None
        self.callback = lambda e: None
        self.clocks = [0, 0]

    def reset(self):
        self.customrules = []
        self.fluidrules = []
        self.synth.router_clear()
        if self.fluid_default:
            self.synth.router_default()

    def add(self, type, chan=None, num=None, val=None, **apars):
        if apars:
            self.customrules.append(CustomRule(type, chan, num, val, **apars))
        elif type[0] != type[1]:
            self.customrules.append(TransRule(type, chan, num, val))
        elif type[0] in ('note', 'kpress', 'cc', 'prog', 'cpress', 'pbend'):
            self.fluidrules.append(FluidRule(type, chan, num, val))
            self.synth.router_clear()
            if self.fluid_default:
                self.synth_router_default()
            # add rules in reverse order because fluidsynth stores them LIFO-style
            for rule in self.fluidrules[::-1]:
                self.synth.router_addrule(rule.type, rule.chan, rule.num, rule.val)

    def handle_midi(self, event):
        self.synth.send_event(event) # pass it along to the fluidsynth router
        t = self.synth.currenttick
        dt = 0
        for rule in list(self.customrules):
            if not rule.applies(event):
                continue
            newevent = rule.apply(event)
            self.callback(newevent) # forward the routed event for user handling
            self.synth.send_event(newevent, route=False) # send routed event directly to synth
            if 'fluidsetting' in rule:
                 self.synth.setting(rule.fluidsetting, newevent.val)
            if 'sequencer' in rule:
                if rule.sequencer in self.synth.players:
                    if 'step' in rule:
                        self.synth.players[rule.sequencer].step(res.event, rule.step) # should be rule.event? new event?
                    self.synth.players[rule.sequencer].play(newevent.val)
            if 'arpeggiator' in rule:
                if rule.arpeggiator in self.synth.players:
                    self.synth.players[rule.arpeggiator].note(newevent.chan, newevent.num, newevent.val)
            if 'midiplayer' in rule:
                if rule.midiplayer in self.synth.players:
                    if 'tick' in rule:
                        self.synth.players[rule.midiplayer].transport(newevent.val, rule.tick)
                    else:
                        self.synth.players[rule.midiplayer].transport(newevent.val)
            if 'tempo' in rule:
                if rule.tempo in self.synth.players:
                    self.synth.players[rule.tempo].set_tempo(newevent.val)
            if 'swing' in rule:
                if rule.swing in self.synth.players:
                    self.synth.players[rule.swing].swing = newevent.val
            if 'groove' in rule:
                if rule.groove in self.synth.players:
                    self.synth.players[rule.groove].groove = [newevent.val]
            if 'sync' in rule:
                if rule.sync in self.synth.players:
                    dt, dt2 = t - self.clocks[0], self.clocks[0] - self.clocks[1]
                    bpm = 1000 * 60 * newevent.val / dt
                    if dt2/dt > 0.5:
                        self.synth.players[rule.sync].set_tempo(bpm)
            if 'ladspafx' in rule:
                if rule.ladspafx in self.synth.ladspafx:
                    self.synth.ladspafx[rule.ladspafx].setcontrol(rule.port, newevent.val)
        if dt > 0:
            self.clocks = t, self.clocks[0]
