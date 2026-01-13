"""
Python handler for fluidsynth midi events
with extensible custom router rules
"""

from .pfluidsynth import PLAYER_TYPES


class RouterEvent:

    def __init__(self, event, rule=None):
        self.__dict__.update(event.__dict__)
        self.rule = rule
        
    def copy(self, **pars):
        e = RouterEvent(self)
        e.__dict__.update(pars)
        return e


class RouterRule:

    def __init__(self, rule):
        self.__dict__.update(rule.__dict__)

    def applies(self, event):
        if self.type != event.type:
            return False
        for par in ("chan", "num", "val"):
            if hasattr(self, par) and hasattr(event, par):
                r = getattr(self, par)
                if r.max < r.min:
                    if r.max < getattr(event, par) < r.min:
                        return False
                elif not (r.min <= getattr(event, par) <= r.max):
                    return False
        return True

    def apply(self, event):
        newevent = RouterEvent(event, self)
        newevent.type = self.totype
        if hasattr(event, "chan"):
            if hasattr(self, "chan"):
                newevent.chan = int(event.chan * self.chan.mul + self.chan.add)
            if hasattr(self, "val"):
                if hasattr(self, "log"):
                    b = 10 ** self.log
                    x = (event.val - self.val.min) / (self.val.max - self.val.min)
                    newevent.val = self.val.tomin + (self.val.tomax - self.val.tomin) * (b ** x - 1) / (b - 1)
                else:
                    newevent.val = event.val * self.val.mul + self.val.add
                if hasattr(self, "lsb"):
                    newevent.lsbval = newevent.val % 127
                    newevent.val //= 127
            if hasattr(self, "num"):
                if self.totype in ("note", "cc", "kpress"):
                    if hasattr(event, "num"):
                        newevent.num = round(event.num * self.num.mul + self.num.add)
                    else:
                        newevent.num = self.num.min
        else:
            if hasattr(self, "chan"):
                newevent.chan = self.chan.min
            if hasattr(self, "num"):
                newevent.num = self.num.min
            if hasattr(self, "val"):
                newevent.val = self.val.min
            elif event.type == "clock":
                newevent.val = 1/24
            elif event.type in ("start", "continue"):
                newevent.val = -1
            elif event.type == "stop":
                newevent.val = 0
        return newevent


class FluidRule:

    def __init__(self, rule):
        self.type = rule.type
        for par in "chan", "num", "val":
            if route := getattr(rule, par, None):
                setattr(self, par, route)


class Router:

    def __init__(self, fluid_default=True, fluid_router=True):
        self.fluid_default = fluid_default
        self.fluid_router = fluid_router
        self.rules = []
        self.fluidrules = []
        self.counters = {}
        self.synth = None
        self.callback = lambda event: None
        self.clocks = [0, 0]

    def reset(self):
        self.rules = []
        self.fluidrules = []
        self.counters = {}
        self.synth.router_clear()
        if self.fluid_default:
            self.synth.router_default()

    def add(self, rule):
        if (
            self.fluid_router
            and rule.type == rule.totype
            and rule.type in ("note", "kpress", "cc", "prog", "cpress", "pbend")
            and not set(rule.__dict__) - {"type", "totype", "chan", "num", "val", "_pars"}
           ):
            if hasattr(rule, "chan"):
                for tochan in rule.chan:
                    self.fluidrules.append(FluidRule(rule.copy(chan=tochan)))
            else:
                self.fluidrules.append(FluidRule(rule))
            self.synth.router_clear()
            if self.fluid_default:
                self.synth_router_default()
            # add rules in reverse order because fluidsynth stores them LIFO-style
            for rule in self.fluidrules[::-1]:
                self.synth.router_addrule(rule)
        else:
            if hasattr(rule, "chan"):
                for tochan in rule.chan:
                    self.rules.append(RouterRule(rule.copy(chan=tochan)))
            else:
                self.rules.append(RouterRule(rule))

    def find_players(self, name):
        return [self.synth.players[ptype][name]
                for ptype in PLAYER_TYPES
                if name in self.synth.players[ptype]]

    def handle_midi(self, event):
        self.synth.send_midievent(event) # pass it along to the fluidsynth router
        self.callback(event) # forward it to the callback
        t = self.synth.currenttick
        dt = 0
        for rule in [r for r in self.rules if r.applies(event)]:
            newevent = rule.apply(event)
            if hasattr(rule, "counter"):
                if rule.counter not in self.counters:
                    self.counters[rule.counter] = getattr(rule, "startval", rule.val.tomin)
                self.counters[rule.counter] += getattr(rule, "inc", 1)
                if self.counters[rule.counter] > rule.val.tomax:
                    self.counters[rule.counter] = rule.val.tomin
                elif self.counters[rule.counter] < rule.val.tomin:
                    self.counters[rule.counter] = rule.val.tomax
                newevent.val = self.counters[rule.counter]
            if hasattr(rule, "lsb"):
                lsbevent = RouterEvent(newevent, rule)
                lsbevent.num, lsbevent.val = rule.lsb, newevent.lsbval
                self.synth.send_midievent(lsbevent, route=False)
            if hasattr(rule, "fluidsetting"):
                self.synth[rule.fluidsetting] = newevent.val
            if hasattr(rule, "play"):
                for player in self.find_players(rule.play):
                    player.play(newevent.val)
            if hasattr(rule, "tempo"):
                for player in self.find_players(rule.tempo):
                    player.set_tempo(newevent.val)
            if hasattr(rule, "tap"):
                for player in self.find_players(rule.tap):
                    dt, dt2 = t - self.clocks[0], self.clocks[0] - self.clocks[1]
                    if dt2/dt > 0.5: # wait for three taps of similar spacing
                        bpm = 1000 * 60 * newevent.val / dt
                        player.set_tempo(bpm)
            if hasattr(rule, "record"):
                for player in self.find_players(rule.record):
                    if hasattr(player, "record"):
                        player.record(newevent.val)
            if hasattr(rule, "arpeggio"):
                for player in self.find_players(rule.arpeggio):
                    if hasattr(player, "add"):
                        player.add(newevent.copy())
                        newevent.val = 0
            if hasattr(rule, "loop"):
                for player in self.find_players(rule.loop):
                    if hasattr(player, "add"):
                        player.add(newevent.copy())
            if hasattr(rule, "swing"):
                for player in self.find_players(rule.swing):
                    if hasattr(player, "set_swing"):
                        player.set_swing(newevent.val)
            if hasattr(rule, "groove"):
                for player in self.find_players(rule.groove):
                    if hasattr(player, "set_groove"):
                        player.set_groove(newevent.val)
            if hasattr(rule, "fx"):
                fx, port = rule.fx.split(">")
                if fx in self.synth.ladspafx:
                    self.synth.ladspafx[fx].setcontrol(port, newevent.val)
            self.synth.send_midievent(newevent, route=False) # send routed event directly to synth
            self.callback(newevent) # forward the routed event for user handling
        if dt > 0:
            self.clocks = t, self.clocks[0]

