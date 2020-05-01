#!/usr/bin/python3
"""
Copyright (c) 2020 Bill Peterson

Description: tries to convert old-style bank files to new ones
             results may vary
"""
import sys
from oyaml import safe_load

f = open(sys.argv[1])
a = safe_load(f)
f.close()

import patcher

b={'patches': {}}
for p in a['patches']:
    b['patches'][p['name']] = {}
    ccmsgs = []
    for chno in p:
        if isinstance(chno, int):
            ch = p[chno]
            sfont = ch['soundfont']
            if 'soundfonts' in a and sfont in a['soundfonts']:
                sfont = a['soundfonts'][sfont]
            b['patches'][p['name']][chno + 1] = patcher.SFPreset(sfont, ch['bank'], ch['program'])
            if 'cc' in ch:
                for cc in ch['cc']:
                    ccmsgs.append(patcher.CCMsg(chno + 1, cc, ch['cc'][cc]))
    if ccmsgs:
        b['patches'][p['name']]['cc'] = patcher.FlowSeq(ccmsgs)
    if 'router_rules' in p:
        rules = []
        for rule in p['router_rules']:
            if rule == 'clear' or rule == 'default':
                rules.append(rule)
            else:
                newrule = {}
                for par in rule:
                    if par == 'type':
                        newrule['type'] = rule['type']
                    elif par == 'chan':
                        min, max, mul, add = rule['chan']
                        if mul == 0: add += 1
                        newrule['chan'] = patcher.RouterSpec(min + 1, max + 1, mul, add)
                    else:
                        newrule[par] = patcher.RouterSpec(*rule[par])
                rules.append(patcher.FlowMap(**newrule))
        b['patches'][p['name']]['router_rules'] = rules
if 'router_rules' in a:
    rules = []
    for rule in a['router_rules']:
        newrule = {}
        for par in rule:
            if par == 'type':
                newrule['type'] = rule['type']
            elif par == 'chan':
                min, max, mul, add = rule['chan']
                if mul == 0: add += 1
                newrule['chan'] = patcher.RouterSpec(min + 1, max + 1, mul, add)
            else:
                newrule[par] = patcher.RouterSpec(*rule[par])
        rules.append(patcher.FlowMap(**newrule))
    b['router_rules'] = rules

fxmap = {
'chorus_level': 'synth.chorus.level',
'chorus_nr': 'synth.chorus.nr',
'chorus_depth': 'synth.chorus.depth',
'chorus_speed': 'synth.chorus.speed',
'reverb_level': 'synth.reverb.level',
'reverb_roomsize': 'synth.reverb.room-size',
'reverb_width': 'synth.reverb.width',
'reverb_damping': 'synth.reverb.damp',
'gain': 'synth.gain'
}
for fr, to in fxmap.items():
    if fr in a:
        b['fluidsettings'] = b.get('fluidsettings', {})
        b['fluidsettings'][to] = a[fr]

if len(sys.argv) > 2:
    f = open(sys.argv[2], 'w')
    patcher.write_yaml(b, f)
    f.close()
else:
    print(patcher.write_yaml(b))
