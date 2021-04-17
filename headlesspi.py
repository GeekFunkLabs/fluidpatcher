#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a headless Raspberry Pi
"""
import time, glob, subprocess
from re import findall
from os import umask
from os.path import relpath, join as joinpath
from sys import argv

import patcher
from utils import netlink

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
# or reprogram your controller to use the corresponding functions
CTRLS_MIDI_CHANNEL = 1
DEC_PATCH = 21          # decrement the patch number
INC_PATCH = 22          # increment the patch number
SELECT_PATCH = 23       # choose a patch using a knob or slider
BANK_INC = 24           # load the next bank


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

def safe_shutdown():
    onboardled_set(0, 1, trigger='mmc0')
    onboardled_set(1, 1, trigger='input')
    subprocess.run('sudo shutdown -h now'.split())

try:
    subprocess.run(('cat', '/sys/class/leds/led1/brightness'), stdout=subprocess.DEVNULL)
except:
    def onboardled_set(led, state=None, trigger=None):
        pass
        
    def onboardled_blink(led, n=0):
        pass
        
    def error_blink(n, e=None):
        if e: raise e    
else:        
    def onboardled_set(led, state=None, trigger=None):
        if trigger:
            e = subprocess.Popen(('echo', trigger), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', '/sys/class/leds/led%s/trigger' % led), stdin=e.stdout, stdout=subprocess.DEVNULL)
        if state != None:
            e = subprocess.Popen(('echo', str(state)), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', '/sys/class/leds/led%s/brightness' % led), stdin=e.stdout, stdout=subprocess.DEVNULL)

    def onboardled_blink(led, n=1):
        while True:            
            onboardled_set(led, 1)
            time.sleep(0.1)
            onboardled_set(led, 0)
            n -= 1
            if n < 1: break
            time.sleep(0.1)
            
    def error_blink(n, e=None):
        # indicate a problem by blinking the PWR led and block forever
        while True:
            onboardled_blink(1, n)
            time.sleep(1)

    onboardled_set(0, 0, trigger='none') # green ACT led off
    onboardled_set(1, 1, trigger='none') # red PWR led on

def headless_synth(cfgfile):
    # start the patcher
    try:
        pxr = patcher.Patcher(cfgfile)
    except patcher.PatcherError as e:
        # problem with config file
        error_blink(2, e)

    def list_banks():
        bpaths = sorted(glob.glob(joinpath(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
        return [relpath(x, start=pxr.bankdir) for x in bpaths]

    def list_soundfonts():
        sfpaths = sorted(glob.glob(joinpath(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
        return [relpath(x, start=pxr.sfdir) for x in sfpaths]

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

    pno = 0
    shutdowntimer = 0
    pxr.select_patch(pno)

    # set up the patch/bank controls
    pxr.link_cc('incpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=INC_PATCH, xfrm='1-127*0+1')
    pxr.link_cc('incpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=DEC_PATCH, xfrm='1-127*0-1')
    pxr.link_cc('shutdowncancel', type='user', chan=CTRLS_MIDI_CHANNEL, cc=INC_PATCH, xfrm='0-0*1+0')
    pxr.link_cc('shutdowncancel', type='user', chan=CTRLS_MIDI_CHANNEL, cc=DEC_PATCH, xfrm='0-0*1+0')
    pxr.link_cc('selectpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=SELECT_PATCH)
    pxr.link_cc('incbank', type='user', chan=CTRLS_MIDI_CHANNEL, cc=BANK_INC, xfrm='1-127*0+1')

    onboardled_blink(0, 5) # ready to play

    # main loop
    while True:
        time.sleep(POLL_TIME)
        t=time.time()
        if shutdowntimer:
            if t - shutdowntimer > 7:
                safe_shutdown()
            if t - shutdowntimer > 5:
                onboardled_blink(1, 10)
                onboardled_set(1, 1)
        changed = pxr.poll_cc()
        if 'incpatch' in changed:
            shutdowntimer = t
            pno = (pno + changed['incpatch']) % pxr.patches_count()
            pxr.select_patch(pno)
            onboardled_blink(0)
        elif 'shutdowncancel' in changed:
            shutdowntimer = 0
        elif 'selectpatch' in changed:
            x = int(changed['selectpatch'] * min(pxr.patches_count(), 128) / 128)
            if x != pno:
                pno = x
                pxr.select_patch(pno)
                onboardled_blink(0)
        elif 'incbank' in changed:
            banks = list_banks()
            if pxr.currentbank in banks:
                bno = banks.index(pxr.currentbank)
            else:
                bno = 0
            bno = (bno + changed['incbank']) % len(banks)
            try:
                onboardled_set(0, 1)
                pxr.load_bank(banks[bno])
                onboardled_set(0, 0)
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
                    onboardled_blink(0)
                    
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
                onboardled_blink(0)

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
    umask(0o002)

    if '--interactive' in argv:
        argv.remove('--interactive')
        def error_blink(n, e=None):
            if e: raise e
            
        def safe_shutdown():
            print('bye!')
            onboardled_set(0, 0, trigger='mmc0')
            onboardled_set(1, 1, trigger='input')
            exit()

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

