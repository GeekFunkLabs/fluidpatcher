#!/usr/bin/python3
"""
Copyright (c) 2020 Bill Peterson

Description: an implementation of patcher.py for a headless Raspberry Pi
"""
import time, sys, re, subprocess
import patcher

SELECT_CH = 10
DEC_CC = 27
INC_CC = 28

POLL_TIME = 0.025

def poll_cc(p):
    x = 0
    if p.fluid.get_cc(SELECT_CH - 1, DEC_CC) != 0:
        x = -1
    elif p.fluid.get_cc(SELECT_CH - 1, INC_CC) != 0:
        x = 1
    p.fluid.send_cc(SELECT_CH - 1, DEC_CC, 0)
    p.fluid.send_cc(SELECT_CH - 1, INC_CC, 0)
    return x        

def alsamidi_reconnect():
    # hack needed for old versions of fluidsynth
    x = re.search(b"client (\d+:) 'FLUID Synth", subprocess.check_output(['aconnect', '-o']))
    if not x:
        raise patcher.PatcherError("Fluid MIDI port not found")
    fluid_port = x.group(1).decode() + '0'
    for client in subprocess.check_output(['aconnect', '-i']).split(b'client'):
        x = re.match(b" (\d+:) '([ \w]*)'", client)
        if not x: continue
        if x.group(2) == b'System': continue
        if x.group(2) == b'Midi Through': continue
        for n in re.findall(b"\n +(\d+) '", client):
            client_port = x.group(1) + n
            subprocess.run(['aconnect', client_port, fluid_port]) 

def onboardled_blink(n):
    e = subprocess.Popen(('sudo', 'echo', 'none'), stdout=subprocess.PIPE)
    subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/trigger'), stdin = e.stdout)
    while True:
        for i in range(n):
            e = subprocess.Popen(('sudo', 'echo', '1'), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/brightness'), stdin = e.stdout)
            time.sleep(0.1)
            e = subprocess.Popen(('sudo', 'echo', '0'), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/brightness'), stdin = e.stdout)
            time.sleep(0.1)
        time.sleep(1)            

# start the patcher
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = '/home/pi/SquishBox/squishboxconf.yaml'
try:
    pxr = patcher.Patcher(cfgfile)
except patcher.PatcherError:
    onboardled_blink(2)

# load bank
try:
    pxr.load_bank(pxr.cfg['currentbank'])
except patcher.PatcherError:
    onboardled_blink(3)

pno = 0
pxr.select_patch(pno)
alsamidi_reconnect()

# main loop
while True:
    time.sleep(POLL_TIME)
    x = poll_cc(pxr)
    if x != 0:
        pno = (pno + x) % pxr.patches_count()
        pxr.select_patch(pno)
