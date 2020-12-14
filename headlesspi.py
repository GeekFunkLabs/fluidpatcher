#!/usr/bin/env python3
"""
Copyright (c) 2020 Bill Peterson

Description: an implementation of patcher.py for a headless Raspberry Pi
"""
import glob, subprocess
from re import findall
from time import sleep
from os.path import relpath, join as joinpath
from sys import argv
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
    for port, client in findall(" (\d+): '([^\n]*)'", x):
        if client == 'System': continue
        if client == 'Midi Through': continue
        if 'FLUID Synth' in client:
            midiports['FLUID Synth'] = port
        else:
            midiports[client] = port
    return midiports

def list_banks():
    bpaths = sorted(glob.glob(joinpath(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
    return [relpath(x, start=pxr.bankdir) for x in bpaths]

def list_soundfonts():
    sfpaths = sorted(glob.glob(joinpath(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
    return [relpath(x, start=pxr.sfdir) for x in sfpaths]

def onboardled_set(state=1):
    e = subprocess.Popen(('sudo', 'echo', str(state)), stdout=subprocess.PIPE)
    subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/brightness'), stdin = e.stdout)

def onboardled_blink():
    onboardled_set(1)
    sleep(0.1)
    onboardled_set(0)
    
def error_blink(n):
    # indicate a problem by blinking one of the onboard LEDs and block forever
    while True:
        for i in range(n):
            onboardled_blink()
            sleep(0.1)
        sleep(1)            


def headless_synth(cfgfile):
    # start the patcher
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
        sleep(POLL_TIME)
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

            if req.type == netlink.SEND_VERSION:
                remote_link.reply(req, patcher.VERSION)
            
            elif req.type == netlink.RECV_BANK:
                try:
                    pxr.load_bank(req.body)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, ','.join(pxr.patch_names()))
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
                    rawbank = pxr.load_bank(req.body)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    info = patcher.write_yaml(pxr.cfg['currentbank'], rawbank, pxr.patch_names())
                    remote_link.reply(req, info)
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
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, warn)
                    pno = int(req.body)
                    onboardled_blink()
                    
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
                
            elif req.type == netlink.READ_CFG:
                info = patcher.write_yaml(pxr.cfgfile, pxr.read_config())
                remote_link.reply(req, info)

            elif req.type == netlink.SAVE_CFG:
                try:
                    pxr.write_config(req.body)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req)


if __name__ == "__main__":
    onboardled_set(0)

    if len(argv) > 1:
        cfgfile = argv[1]
    else:
        cfgfile = '/home/pi/SquishBox/squishboxconf.yaml'

    try:
        headless_synth(cfgfile)
    except:
        error_blink(4)
