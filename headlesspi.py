#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a headless Raspberry Pi
    creates a synthesizer that can be controlled with a USB MIDI controller
    patches/banks are changed using pads/buttons/knobs on the controller
    should work on other platforms as well
"""
import time, re, sys, os, traceback, glob, subprocess, mido, simpleaudio
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
ACT_LED = 0
PWR_LED = 1

if not os.path.exists('/sys/class/leds/led1/brightness'):
    PWR_LED = 0 # Pi Zero only has ACT led
if not os.path.exists('/sys/class/leds/led0/brightness'):
    # no leds - testing on non-RPi
    def onboardled_set(led, state=None, trigger=None):
        pass
        
    def onboardled_blink(led, n=0):
        pass
        
    def error_blink(n):
        pass
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
            
    def error_blink(n):
        # indicate a problem by blinking the PWR led and block forever
        while True:
            onboardled_blink(PWR_LED, n)
            time.sleep(1)

    def headless_excepthook(etype, val, tb):
        if etype == KeyboardInterrupt:
            sys.exit()
        traceback.print_exception(etype, val, tb)
        error_blink(4)
    sys.excepthook = headless_excepthook

    onboardled_set(PWR_LED, 1, trigger='none') # red PWR led on
    onboardled_set(ACT_LED, 0, trigger='none') # green ACT led off

def list_banks():
    bpaths = sorted(glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
    return [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]

def list_soundfonts():
    sfpaths = sorted(glob.glob(os.path.join(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
    return [os.path.relpath(x, start=pxr.sfdir) for x in sfpaths]

def select_patch(n):
    pxr.select_patch(n)
    onboardled_blink(ACT_LED)
    print("Selected patch %d/%d: %s" % (n + 1, pxr.patches_count(), pxr.patch_name(n)))

def load_bank(bfile, quiet = False):
    onboardled_set(ACT_LED, 1)
    if not quiet: play_sound('bank_loading')
    print("Loading bank '%s' .. " % bfile, end='')
    pxr.load_bank(bfile)
    onboardled_set(ACT_LED, 0)
    if not quiet: play_sound('bank_loaded')
    print("done!")

def play_sound(sound):
    if pxr.cfg.get('audiofeedback', 0):
        simpleaudio.WaveObject.from_wave_file(f'audiofeedback/{sound}.wav').play()

os.umask(0o002)
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = 'SquishBox/squishboxconf.yaml'

# start the patcher
try:
    pxr = patcher.Patcher(cfgfile)
except patcher.PatcherError as e:
    print("Error(s) in " + cfgfile, file=sys.stderr)
    error_blink(2)

# hack to connect MIDI devices to old versions of fluidsynth
fport = re.search("client (\d+): 'FLUID Synth", subprocess.check_output(['aconnect', '-o']).decode())[1]
for port, client in re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-i']).decode()):
    if client == 'Midi Through': continue
    subprocess.run(['aconnect', port, fport])
        
# initialize network link
if pxr.cfg.get('remotelink_active', 1): # allow link by default
    port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
    passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
    remote_link = netlink.Server(port, passkey)
else:
    remote_link = None

# load bank
try:
    load_bank(pxr.currentbank, True)
except patcher.PatcherError as e:
    print("Error(s) in " + pxr.currentbank, file=sys.stderr)
    error_blink(3)

pno = 0
shutdowntimer = 0
select_patch(pno)

# set up the patch/bank controls
pxr.link_cc('incpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=INC_PATCH, xfrm='1-127*0+1')
pxr.link_cc('incpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=DEC_PATCH, xfrm='1-127*0-1')
pxr.link_cc('shutdowncancel', type='user', chan=CTRLS_MIDI_CHANNEL, cc=INC_PATCH, xfrm='0-0*1+0')
pxr.link_cc('shutdowncancel', type='user', chan=CTRLS_MIDI_CHANNEL, cc=DEC_PATCH, xfrm='0-0*1+0')
pxr.link_cc('selectpatch', type='user', chan=CTRLS_MIDI_CHANNEL, cc=SELECT_PATCH)
pxr.link_cc('incbank', type='user', chan=CTRLS_MIDI_CHANNEL, cc=BANK_INC, xfrm='1-127*0+1')

onboardled_blink(ACT_LED, 5) # ready to play
play_sound('boot_up')

# main loop
while True:
    time.sleep(POLL_TIME)
    t=time.time()
    if shutdowntimer:
        if t - shutdowntimer > 7:
            onboardled_set(ACT_LED, 1, trigger='mmc0')
            onboardled_set(PWR_LED, 1, trigger='input')
            print("Shutting down..")
            play_sound('shut_down')
            time.sleep(0.75)
            subprocess.run('sudo shutdown -h now'.split())
        if t - shutdowntimer > 5:
            play_sound('will_shut_down')
            onboardled_blink(PWR_LED, 11)
            onboardled_set(PWR_LED, 1)
    changed = pxr.poll_cc()
    if 'incpatch' in changed:
        shutdowntimer = t
        pno = (pno + changed['incpatch']) % pxr.patches_count()
        play_sound('patch_change')
        select_patch(pno)
    elif 'shutdowncancel' in changed:
        shutdowntimer = 0
    elif 'selectpatch' in changed:
        x = int(changed['selectpatch'] * min(pxr.patches_count(), 128) / 128)
        if x != pno:
            pno = x
            select_patch(pno)
    elif 'incbank' in changed:
        banks = list_banks()
        if pxr.currentbank in banks:
            bno = banks.index(pxr.currentbank)
        else:
            bno = 0
        bno = (bno + changed['incbank']) % len(banks)
        try:
            load_bank(banks[bno])
            pno = 0
            select_patch(pno)
        except patcher.PatcherError as e:
            print(repr(e), file=sys.stderr)
            error_blink(3)
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
                onboardled_set(ACT_LED, 1)
                if req.body == '':
                    rawbank = pxr.load_bank()
                else:
                    rawbank = pxr.load_bank(req.body)
                onboardled_set(ACT_LED, 0)
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
                onboardled_blink(ACT_LED)
                
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
            onboardled_blink(ACT_LED)

        elif req.type == netlink.LIST_PLUGINS:
            try:
                info = subprocess.check_output(['listplugins']).decode()
            except:
                remote_link.reply(req, 'No plugins installed')
            else:
                remote_link.reply(req, patcher.write_yaml(info))

        elif req.type == netlink.LIST_PORTS:
            ports = mido.get_input_names()
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
