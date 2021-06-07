#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a headless Raspberry Pi
    creates a synthesizer that can be controlled with a USB MIDI controller
    patches/banks are changed using pads/buttons/knobs on the controller
    should work on other platforms as well
"""
import time, re, sys, os, traceback, glob, subprocess
import patcher
from utils import netlink

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
# or reprogram your controller to use the corresponding functions
CTRLS_MIDI_CHANNEL = 1
DEC_PATCH = 21          # decrement the patch number
INC_PATCH = 22          # increment the patch number
SELECT_PATCH = 23       # choose a patch using a knob or slider
BANK_INC = 24           # load the next bank


def connect_controls():
	pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=DEC_PATCH, patch=-1)
	pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=INC_PATCH, patch=-1)
	pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=SELECT_PATCH, patch='select')
	pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=BANK_INC, par2='1-127', bank=1)

# toggling the onboard LEDs requires writing to the SD card, which can cause audio stutters
# this is not usually noticeable, since it only happens when switching patches or shutting down
# but if it becomes annoying, LED control can be disabled here
DISABLE_LED = False

POLL_TIME = 0.025
ACT_LED = 0
PWR_LED = 1

if not os.path.exists('/sys/class/leds/led1/brightness'):
    PWR_LED = 0 # Pi Zero only has ACT led
if not os.path.exists('/sys/class/leds/led0/brightness') or DISABLE_LED:
    # leds don't exist or control disabled
    def onboardled_set(led, state=None, trigger=None):
        pass
        
    def onboardled_blink(led, n=0):
        pass
        
    def error_blink(n):
        sys.exit()
        
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

def load_bank(bfile):
    onboardled_set(ACT_LED, 1)
    print(f"Loading bank '{bfile}' .. ", end='')
    try:
        pxr.load_bank(bfile)
    except patcher.PatcherError as e:
        print("Error(s) in " + pxr.currentbank)
        error_blink(3)
    print("done!")
    onboardled_set(ACT_LED, 0)

def select_patch(n):
    pxr.select_patch(n)
    connect_controls()
    onboardled_blink(ACT_LED)
    print(f"Selected patch {n + 1}/{pxr.patches_count()}: {pxr.patch_name(n)}")


class App():

    def __init__(self):
        self.pno = 0
        self.shutdowntimer = 0
        load_bank(pxr.currentbank)
        select_patch(self.pno)

    def mainloop(self):
        while True:
            time.sleep(POLL_TIME)
            t=time.time()
            self.poll_remotelink()
            if self.shutdowntimer:
                if t - self.shutdowntimer > 7:
                    onboardled_set(ACT_LED, 1, trigger='mmc0')
                    onboardled_set(PWR_LED, 1, trigger='input')
                    print("Shutting down..")
                    subprocess.run('sudo shutdown -h now'.split())
                if t - self.shutdowntimer > 5:
                    onboardled_blink(PWR_LED, 10)
                    onboardled_set(PWR_LED, 1)

    def listener(self, msg):
        if hasattr(msg, 'patch'):
            if msg.patch == 'select':
                x = int(msg.val * min(pxr.patches_count(), 128) / 128)
                if x != self.pno:
                    self.pno = x
                    select_patch(self.pno)
            else:
                if msg.val > 0:
                    shutdowntimer = time.time()
                    self.pno = round(self.pno + msg.patch) % pxr.patches_count()
                    select_patch(self.pno)
                else:
                    shutdowntimer = 0
        elif hasattr(msg, 'bank'):
            banks = list_banks()
            if pxr.currentbank in banks:
                bno = (banks.index(pxr.currentbank) + 1 ) % len(banks)
            else:
                bno = 0
            load_bank(banks[bno])
            self.pno = 0
            select_patch(self.pno)
            pxr.write_config()    

    def poll_remotelink(self):
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
                    remote_link.reply(req, patcher.render_fpyaml(pxr.patch_names()))
                    
            elif req.type == netlink.LIST_BANKS:
                banks = list_banks()
                if not banks:
                    remote_link.reply(req, "no banks found!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.render_fpyaml(banks))
                
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
                    info = patcher.render_fpyaml(pxr.currentbank, rawbank, pxr.patch_names())
                    remote_link.reply(req, info)
                    pxr.write_config()
                    
            elif req.type == netlink.SAVE_BANK:
                bfile, rawbank = patcher.parse_fpyaml(req.body)
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
                        self.pno = int(req.body)
                    else:
                        self.pno = pxr.patch_index(req.body)
                    warn = pxr.select_patch(self.pno)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, warn)
                    onboardled_blink(ACT_LED)
                    
            elif req.type == netlink.LIST_SOUNDFONTS:
                sf = list_soundfonts()
                if not sf:
                    remote_link.reply(req, "No soundfonts!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.render_fpyaml(sf))
            
            elif req.type == netlink.LOAD_SOUNDFONT:
                if not pxr.load_soundfont(req.body):
                    remote_link.reply(req, "Unable to load " + req.body, netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, patcher.render_fpyaml(pxr.sfpresets))
            
            elif req.type == netlink.SELECT_SFPRESET:
                self.pno = int(req.body)
                warn = pxr.select_sfpreset(self.pno)
                remote_link.reply(req, warn)
                onboardled_blink(ACT_LED)

            elif req.type == netlink.LIST_PLUGINS:
                try:
                    info = subprocess.check_output(['listplugins']).decode()
                except:
                    remote_link.reply(req, 'No plugins installed')
                else:
                    remote_link.reply(req, patcher.render_fpyaml(info))

            elif req.type == netlink.LIST_PORTS:
                ports = patcher.list_midi_inputs()
                remote_link.reply(req, patcher.render_fpyaml(ports))
                
            elif req.type == netlink.READ_CFG:
                info = patcher.render_fpyaml(pxr.cfgfile, pxr.read_config())
                remote_link.reply(req, info)

            elif req.type == netlink.SAVE_CFG:
                try:
                    pxr.write_config(req.body)
                except patcher.PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req)



os.umask(0o002)
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = 'SquishBox/squishboxconf.yaml'

# start the patcher
try:
    pxr = patcher.Patcher(cfgfile)
except patcher.PatcherError as e:
    print("Error(s) in " + cfgfile)
    error_blink(2)

# hack to connect MIDI devices to old versions of fluidsynth
fport = re.search("client (\d+): 'FLUID Synth", subprocess.check_output(['aconnect', '-o']).decode())[1]
for port, client in re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-i']).decode()):
    subprocess.run(['aconnect', port, fport])
        
# initialize network link
if pxr.cfg.get('remotelink_active', 1): # specify remotelink_active: 0 in cfgfile if not desired
    port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
    passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
    remote_link = netlink.Server(port, passkey)
else:
    remote_link = None

app = App()
pxr.set_midimessage_callback(app.listener)
onboardled_blink(ACT_LED, 5) # ready to play
app.mainloop()
