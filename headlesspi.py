#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a headless Raspberry Pi
    creates a synthesizer that can be controlled with a USB MIDI controller
    patches/banks are changed using pads/buttons/knobs on the controller
    should work on other platforms as well
"""
import time, re, sys, os, traceback, subprocess
import patcher

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
# or reprogram your controller to send the corresponding messages
CTRLS_MIDI_CHANNEL = 1
DEC_PATCH = 21          # decrement the patch number
INC_PATCH = 22          # increment the patch number
SELECT_PATCH = 23       # choose a patch using a knob or slider
BANK_INC = 24           # load the next bank

# toggling the onboard LEDs requires writing to the SD card, which can cause audio stutters
# this is not usually noticeable, since it only happens when switching patches or shutting down
# but if it becomes annoying, LED control can be disabled here
DISABLE_LED = False

# modify this function directly if you want to change patches using notes or other MIDI messages
def connect_controls():
    pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=DEC_PATCH, patch=-1)
    pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=INC_PATCH, patch=1)
    pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=SELECT_PATCH, patch='select')
    pxr.add_router_rule(type='cc', chan=CTRLS_MIDI_CHANNEL, par1=BANK_INC, par2='1-127', bank=1)


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
        # catch all errors, quit if Ctrl+C was pressed
        # otherwise error_blink(4) forever if headless
        # and also print error to stdout if running from console
        if etype == KeyboardInterrupt:
            sys.exit()
        traceback.print_exception(etype, val, tb)
        error_blink(4)
    sys.excepthook = headless_excepthook

    onboardled_set(PWR_LED, 1, trigger='none') # red PWR led on
    onboardled_set(ACT_LED, 0, trigger='none') # green ACT led off


class HeadlessSynth:

    def __init__(self):
        self.shutdowntimer = 0
        self.lastpoll = time.time()
        pxr.set_midimessage_callback(self.listener)
        self.load_bank(pxr.currentbank)
        onboardled_blink(ACT_LED, 5) # ready to play
        while True:
            time.sleep(POLL_TIME)
            if self.shutdowntimer:
                t = time.time()
                if t - self.shutdowntimer > 7:
                    onboardled_set(ACT_LED, 1, trigger='mmc0')
                    onboardled_set(PWR_LED, 1, trigger='input')
                    print("Shutting down..")
                    subprocess.run('sudo shutdown -h now'.split())
                if t - self.shutdowntimer > 5:
                    onboardled_blink(PWR_LED, 10)
                    onboardled_set(PWR_LED, 1)

    def load_bank(self, bfile):
        print(f"Loading bank '{bfile}' .. ")
        onboardled_set(ACT_LED, 1)
        try:
            pxr.load_bank(bfile)
        except Exception as e:
            print(f"Error loading {bfile}\n{str(e)}")
            error_blink(3)
        print("Bank loaded.")
        onboardled_set(ACT_LED, 0)
        self.pno = 0
        if pxr.patches:
            self.select_patch(self.pno)
        else:
            pxr.select_patch(None)
            connect_controls()
            print("No patches")

    def select_patch(self, n):
        pxr.select_patch(n)
        connect_controls()
        print(f"Selected patch {n + 1}/{len(pxr.patches)}: {pxr.patches[n]}")
        onboardled_blink(ACT_LED)

    def listener(self, msg):
    # catches custom midi :msg to change patch/bank
        if hasattr(msg, 'patch') and pxr.patches:
            if msg.patch == 'select':
                x = int(msg.val * min(len(pxr.patches), 128) / 128)
                if x != self.pno:
                    self.pno = x
                    self.select_patch(self.pno)
            else:
                if msg.val > 0:
                    self.shutdowntimer = time.time()
                    self.pno = round(self.pno + msg.patch) % len(pxr.patches)
                    self.select_patch(self.pno)
                else:
                    self.shutdowntimer = 0
        elif hasattr(msg, 'bank'):
            if pxr.currentbank in pxr.banks:
                bno = (pxr.banks.index(pxr.currentbank) + 1 ) % len(pxr.banks)
            else:
                bno = 0
            self.load_bank(pxr.banks[bno])
            pxr.write_config()    


cfgfile = sys.argv[1] if len(sys.argv) > 1 else 'SquishBox/squishboxconf.yaml'
try:
    pxr = patcher.Patcher(cfgfile)
except Exception as e:
    print(f"Error loading config file {cfgfile}\n{str(e)}")
    error_blink(2)

# hack to connect MIDI devices to old versions of fluidsynth
fport = re.search("client (\d+): 'FLUID Synth", subprocess.check_output(['aconnect', '-o']).decode())[1]
for port, client in re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-i']).decode()):
    subprocess.run(['aconnect', port, fport])

mainapp = HeadlessSynth()
