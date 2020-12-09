#!/usr/bin/env python3
"""
Copyright (c) 2020 Bill Peterson

Description: an implementation of patcher.py for a headless Raspberry Pi
"""
import time, sys, os, re, glob, subprocess
import patcher
from utils import netlink

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
PATCH_SELECT_CHANNEL = 10
DEC_CC = 27
INC_CC = 28
# uncomment and modify this if using a knob/slider to select patch
# SELECT_CC = 29


POLL_TIME = 0.025

def list_midiports():
    midiports = {}
    x = subprocess.check_output(['aconnect', '-o']).decode()
    for port, client in re.findall(" (\d+): '([^\n]*)'", x):
        if client == 'System': continue
        if client == 'Midi Through': continue
        if 'FLUID Synth' in client:
            midiports['FLUID Synth'] = port
        else:
            midiports[client] = port
    return midiports

def list_banks():
    bpaths = sorted(glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
    return [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]

def list_soundfonts():
    sfpaths = sorted(glob.glob(os.path.join(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
    return [os.path.relpath(x, start=pxr.sfdir) for x in sfpaths]

def onboardled_set(state=1):
    e = subprocess.Popen(('sudo', 'echo', str(state)), stdout=subprocess.PIPE)
    subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/brightness'), stdin = e.stdout)

def onboardled_blink():
    onboardled_set(0)
    time.sleep(0.1)
    onboardled_set(1)
    
def error_blink(n):
    # indicate a problem by blinking one of the onboard LEDs and block forever
    while True:
        for i in range(n):
            onboardled_blink()
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
    # problem with config file
    error_blink(2)

# hack to connect MIDI devices to old versions of fluidsynth
midiports = list_midiports()
for client in midiports:
    if client == 'FLUID Synth': continue
    subprocess.run(['aconnect', midiports[client], midiports['FLUID Synth']])
        
# initialize network link
if pxr.cfg.get('remotelink_active', 1):
    port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
    passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
    remote_link = netlink.Server(port, passkey)
else:
    remote_link = None

# load bank
try:
    pxr.load_bank(pxr.cfg['currentbank'])
except patcher.PatcherError:
    # problem with bank file
    error_blink(3)

pxr.link_cc('inc', type='patch', chan=PATCH_SELECT_CHANNEL, cc=INC_CC)
pxr.link_cc('dec', type='patch', chan=PATCH_SELECT_CHANNEL, cc=DEC_CC)
if 'SELECT_CC' in locals():
    pxr.link_cc('select', type='patch', chan=PATCH_SELECT_CHANNEL, cc=SELECT_CC)
pno = 0
pxr.select_patch(pno)


# main loop
while True:
    time.sleep(POLL_TIME)
    changed = pxr.poll_cc()
    if 'patch' in changed:
        pno = (pno + changed['patch']) % pxr.patches_count()
        pxr.select_patch(pno)
        onboardled_blink()
    if 'selectpatch' in changed:
        x = int(changed['selectpatch'] * pxr.patches_count() / 128)
        if x != pno:
            pno = x
            pxr.select_patch(pno)
            onboardled_blink()


    # check remote link for requests and process them
    if remote_link and remote_link.pending():
        req = remote_link.requests.pop(0)
        
        if req.type == netlink.SEND_STATE:
            state = patcher.write_yaml(pxr.bank, pxr.patch_name(), pxr.cfg['currentbank'])
            remote_link.reply(req, state)

        elif req.type == netlink.RECV_BANK:
            try:
                pxr.load_bank(req.body)
            except patcher.PatcherError as e:
                remote_link.reply(req, str(e), netlink.REQ_ERROR)
            else:
                remote_link.reply(req, ','.join(pxr.patch_name()))
                pno = 0
                pxr.select_patch(pno)
                
        elif req.type == netlink.LIST_BANKS:
            banks = list_banks()
            if not banks:
                remote_link.reply(req, "no banks found!", netlink.REQ_ERROR)
            else:
                remote_link.reply(req, ','.join(banks))
            
        elif req.type == netlink.LOAD_BANK:
            try:
                pxr.load_bank(req.body)
            except patcher.PatcherError as e:
                remote_link.reply(req, str(e), netlink.REQ_ERROR)
            else:
                state = patcher.write_yaml(pxr.bank, pxr.patch_name())
                remote_link.reply(req, state)
                pno = 0
                pxr.select_patch(pno)
                pxr.write_config()
                
        elif req.type == netlink.SAVE_BANK:
            bfile, rawbank = patcher.read_yaml(req.body)
            try:
                pxr.save_bank(bfile, rawbank)
            except patcher.PatcherError as e:
                remote_link.reply(req, str(e), netlink.REQ_ERROR)
            else:
                remote_link.reply(req)
                pxr.write_config()
                        
        elif req.type == netlink.SELECT_PATCH:
            try:
                warn = pxr.select_patch(int(req.body))
            except patcher.PatcherError as e:
                warn = str(e)
            if warn:
                remote_link.reply(req, warn, netlink.REQ_ERROR)
            else:
                remote_link.reply(req)
                pno = int(req.body)
                
        elif req.type == netlink.LIST_SOUNDFONTS:
            sf = list_soundfonts()
            if not sf:
                remote_link.reply(req, "no soundfonts!", netlink.REQ_ERROR)
            else:
                remote_link.reply(req, ','.join(sf))
        
        elif req.type == netlink.LOAD_SOUNDFONT:
            pxr.load_soundfont(req.body)
            remote_link.reply(req, patcher.write_yaml(pxr.sfpresets))
            pno = 0
            pxr.select_sfpreset(pno)
        
        elif req.type == netlink.SELECT_SFPRESET:
            remote_link.reply(req)
            pno = int(req.body)
            pxr.select_sfpreset(pno)

        elif req.type == netlink.LIST_PLUGINS:
            try:
                info = subprocess.check_output(['listplugins']).decode()
            except:
                remote_link.reply(req, 'No plugins installed')
            else:
                remote_link.reply(req, info)

        elif req.type == netlink.LIST_PORTS:
            info = '\n'.join(list_midiports().keys())
            remote_link.reply(req, info)
