#!/usr/bin/env python3
"""
Copyright (c) 2020 Bill Peterson

Description: an implementation of patcher.py for a headless Raspberry Pi
"""
import glob, subprocess
from re import findall
from time import sleep
from os import umask
from os.path import relpath, join as joinpath
from sys import argv
import patcher
from utils import netlink

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
PATCH_INC_CHANNEL = 10
DEC_CC = 25
INC_CC = 26
# uncomment and modify these if using a knob/slider to select patch
#PATCH_SELECT_CHANNEL = 1
#SELECT_CC = 17
# uncomment and modify if you want to be able to switch banks
#BANK_INC_CHANNEL = 10
#BANK_INC_CC = 28


POLL_TIME = 0.025

def scan_midiports():
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

try:
    subprocess.run(('cat', '/sys/class/leds/led1/brightness'), stdout=subprocess.DEVNULL)
except:
    def onboardled_set(state=1):
        pass
        
    def onboardled_blink():
        pass
        
    def error_blink(n, e=None):
        if e: raise e    
else:
    def onboardled_set(state=1):
        e = subprocess.Popen(('echo', str(state)), stdout=subprocess.PIPE)
        subprocess.run(('sudo', 'tee', '/sys/class/leds/led1/brightness'), stdin=e.stdout, stdout=subprocess.DEVNULL)

    def onboardled_blink():
        onboardled_set(1)
        sleep(0.1)
        onboardled_set(0)
        
    def error_blink(n, e=None):
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
    except patcher.PatcherError as e:
        # problem with config file
        error_blink(2, e)

    # hack to connect MIDI devices to old versions of fluidsynth
    midiports = scan_midiports()
    for client in midiports:
        if client == 'FLUID Synth': continue
        subprocess.run(['aconnect', midiports[client], midiports['FLUID Synth']])
            
    # initialize network link
    if pxr.cfg.get('remotelink_active', 1): # allow link by default
        port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
        passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
        remote_link = netlink.Server(port, passkey)
    else:
        remote_link = None

    # load bank
    try:
        pxr.load_bank(pxr.currentbank)
    except patcher.PatcherError as e:
        # problem with bank file
        error_blink(3, e)

    pxr.link_cc('incpatch', type='patch', chan=PATCH_INC_CHANNEL, cc=INC_CC, xfrm='1-127*0+1')
    pxr.link_cc('incpatch', type='patch', chan=PATCH_INC_CHANNEL, cc=DEC_CC, xfrm='1-127*0-1')
    if 'PATCH_SELECT_CHANNEL' in globals():
        pxr.link_cc('selectpatch', type='patch', chan=PATCH_SELECT_CHANNEL, cc=SELECT_CC)
    if 'BANK_INC_CHANNEL' in globals():
        pxr.link_cc('incbank', type='bank', chan=BANK_INC_CHANNEL, cc=BANK_INC_CC, xfrm='1-127*0+1')
    pno = 0
    pxr.select_patch(pno)

    def list_banks():
        bpaths = sorted(glob.glob(joinpath(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
        return [relpath(x, start=pxr.bankdir) for x in bpaths]

    def list_soundfonts():
        sfpaths = sorted(glob.glob(joinpath(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
        return [relpath(x, start=pxr.sfdir) for x in sfpaths]


    # main loop
    while True:
        sleep(POLL_TIME)
        changed = pxr.poll_cc()
        if 'incpatch' in changed:
            pno = (pno + changed['incpatch']) % pxr.patches_count()
            pxr.select_patch(pno)
            onboardled_blink()
        elif 'selectpatch' in changed:
            x = int(changed['selectpatch'] * min(pxr.patches_count(), 128) / 128)
            if x != pno:
                pno = x
                pxr.select_patch(pno)
                onboardled_blink()
        elif 'incbank' in changed:
            banks = list_banks()
            if pxr.currentbank in banks:
                bno = banks.index(pxr.currentbank)
            else:
                bno = 0
            bno = (bno + changed['incbank']) % len(banks)
            try:
                onboardled_set(1)
                pxr.load_bank(banks[bno])
                onboardled_set(0)
                pno = 0
                pxr.select_patch(pno)
            except patcher.PatcherError as e:
                error_blink(3, e)
            else:
                pxr.write_config()    

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
                    remote_link.reply(req, patcher.write_yaml(pxr.patch_names()))
                    
            elif req.type == netlink.LIST_BANKS:
                banks = list_banks()
                if not banks:
                    remote_link.reply(req, "no banks found!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.write_yaml(banks))
                
            elif req.type == netlink.LOAD_BANK:
                try:
                    if req.body == '':
                        rawbank = pxr.load_bank()
                    else:
                        rawbank = pxr.load_bank(req.body)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    info = patcher.write_yaml(pxr.currentbank, rawbank, pxr.patch_names())
                    remote_link.reply(req, info)
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
                    if req.body.isdecimal():
                        pno = int(req.body)
                    else:
                        pno = pxr.patch_index(req.body)
                    warn = pxr.select_patch(pno)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, warn)
                    onboardled_blink()
                    
            elif req.type == netlink.LIST_SOUNDFONTS:
                sf = list_soundfonts()
                if not sf:
                    remote_link.reply(req, "no soundfonts!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.write_yaml(sf))
            
            elif req.type == netlink.LOAD_SOUNDFONT:
                if not pxr.load_soundfont(req.body):
                    remote_link.reply(req, "Unable to load %s" % req.body, netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.write_yaml(pxr.sfpresets))
            
            elif req.type == netlink.SELECT_SFPRESET:
                pno = int(req.body)
                warn = pxr.select_sfpreset(pno)
                remote_link.reply(req, warn)
                onboardled_blink()

            elif req.type == netlink.LIST_PLUGINS:
                try:
                    info = subprocess.check_output(['listplugins']).decode()
                except:
                    remote_link.reply(req, 'No plugins installed')
                else:
                    remote_link.reply(req, patcher.write_yaml(info))

            elif req.type == netlink.LIST_PORTS:
                ports = list(scan_midiports().keys())
                remote_link.reply(req, patcher.write_yaml(ports))
                
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
    umask(0o002)

    if '--interactive' in argv:
        argv.remove('--interactive')
        def error_blink(n, e=None):
            if e: raise e    

    if len(argv) > 1:
        cfgfile = argv[1]
    else:
        cfgfile = 'SquishBox/squishboxconf.yaml'

    try:
        headless_synth(cfgfile)
    except KeyboardInterrupt:
        exit(1)
    except Exception as e:
        error_blink(4, e)

