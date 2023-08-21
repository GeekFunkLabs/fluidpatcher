#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a headless Raspberry Pi
    creates a synthesizer that can be controlled with a USB MIDI controller
    patches/banks are changed using pads/buttons/knobs on the controller
    should work on other platforms as well
"""
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

from fluidpatcher import FluidPatcher

# change these values to correspond to buttons/pads on your MIDI keyboard/controller
# or reprogram your controller to send the corresponding messages
CHAN = 1
TYPE = 'cc'             # 'cc' or 'note'
DEC_PATCH = 21          # decrement the patch number
INC_PATCH = 22          # increment the patch number
BANK_INC = 23           # load the next bank

# a continuous controller e.g. knob/slider can be used to select patches by value
SELECT_PATCH = None

# hold this button down for 7 seconds to safely shut down the Pi
# if this = None the patch change buttons are used
SHUTDOWN_BTN = None

# toggling the onboard LEDs requires writing to the SD card, which can cause audio stutters
# this is not usually noticeable, since it only happens when switching patches or shutting down
# but if it becomes annoying, LED control can be disabled here
DISABLE_LED = False


def connect_controls():
    fp.add_router_rule(type=TYPE, chan=CHAN, par1=DEC_PATCH, par2='1-127', patch='1-')
    fp.add_router_rule(type=TYPE, chan=CHAN, par1=INC_PATCH, par2='1-127', patch='1+')
    fp.add_router_rule(type=TYPE, chan=CHAN, par1=BANK_INC, par2='1-127', bank=1)
    if SELECT_PATCH != None:
        selectspec =  f"0-127=0-{min(len(fp.patches) - 1, 127)}" # transform CC values into patch numbers
        fp.add_router_rule(type='cc', chan=CHAN, par1=SELECT_PATCH, par2=selectspec, patch='select')
    if SHUTDOWN_BTN != None:
        fp.add_router_rule(type=TYPE, chan=CHAN, par1=SHUTDOWN_BTN, shutdown=1)
    else:
        fp.add_router_rule(type=TYPE, chan=CHAN, par1=DEC_PATCH, shutdown=1)
        fp.add_router_rule(type=TYPE, chan=CHAN, par1=INC_PATCH, shutdown=1)

POLL_TIME = 0.025
ACT_LED = ''
for path in [Path('/sys/class/leds/led0'), Path('/sys/class/leds/ACT')]:
    if path.exists():
        ACT_LED = path
for path in [Path('/sys/class/leds/led1'), Path('/sys/class/leds/PWR')]:
    if path.exists():
        PWR_LED = path
        break
else:
    PWR_LED = ACT_LED # Pi Zero only has ACT led

if not ACT_LED or DISABLE_LED:
    # no led hooks or user disabled
    def onboardled_set(led, state=None, trigger=None): pass
    def onboardled_blink(led, n=0): pass
    def error_blink(n): sys.exit()        
else:
    def onboardled_set(led, state=None, trigger=None):
        if trigger:
            e = subprocess.Popen(('echo', trigger), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', led / 'trigger'), stdin=e.stdout, stdout=subprocess.DEVNULL)
        if state != None:
            e = subprocess.Popen(('echo', str(state)), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', led / 'brightness'), stdin=e.stdout, stdout=subprocess.DEVNULL)

    def onboardled_blink(led, n=1):
        while n:
            onboardled_set(led, 1)
            time.sleep(0.1)
            onboardled_set(led, 0)
            n -= 1
            if n: time.sleep(0.1)
            
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
        self.pno = 0
        fp.midi_callback = self.listener
        self.load_bank(fp.currentbank)
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
                    onboardled_set(PWR_LED, 0)
                    time.sleep(POLL_TIME)
                    onboardled_set(PWR_LED, 1)

    def load_bank(self, bfile):
        print(f"Loading bank '{bfile}' .. ")
        onboardled_set(ACT_LED, 1)
        try:
            fp.load_bank(bfile)
        except Exception as e:
            print(f"Error loading {bfile}\n{str(e)}")
            error_blink(3)
        print("Bank loaded.")
        onboardled_set(ACT_LED, 0)
        if fp.patches:
            self.select_patch(0, force=True)
        else:
            fp.apply_patch('')
            connect_controls()
            print("No patches")

    def select_patch(self, n, force=False):
        if n == self.pno and not force: return
        self.pno = n
        fp.apply_patch(self.pno)
        connect_controls()
        print(f"Selected patch {n + 1}/{len(fp.patches)}: {fp.patches[n]}")
        onboardled_blink(ACT_LED)

    def listener(self, sig):
    # catches custom midi :sig to change patch/bank
        if hasattr(sig, 'patch'):
            if sig.patch < 0:
                self.select_patch((self.pno + sig.val) % len(fp.patches))
            else:
                self.select_patch(sig.patch)
        if hasattr(sig, 'bank') and sig.val > 0:
            banks = sorted([b.relative_to(fp.bankdir) for b in fp.bankdir.rglob('*.yaml')])
            bno = (banks.index(fp.currentbank) + 1 ) % len(banks) if fp.currentbank in banks else 0
            self.load_bank(banks[bno])
            fp.write_config()
        if hasattr(sig, 'shutdown'):
            if self.shutdowntimer:
                self.shutdowntimer = 0
            elif sig.val > 0:
                self.shutdowntimer = time.time()


cfgfile = sys.argv[1] if len(sys.argv) > 1 else 'SquishBox/squishboxconf.yaml'
try:
    fp = FluidPatcher(cfgfile)
except Exception as e:
    print(f"Error loading config file {cfgfile}\n{str(e)}")
    error_blink(2)

devs = {client: port for port, client in re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-io']).decode())}
for link in fp.cfg.get('midiconnections', []):
    mfrom, mto = list(link.items())[0]
    for client in devs:
        if re.search(mfrom.split(':')[0], client):
            mfrom = re.sub(mfrom.split(':')[0], devs[client], mfrom, count=1)
        if re.search(mto.split(':')[0], client):
            mto = re.sub(mto.split(':')[0], devs[client], mto, count=1)
    try:
        subprocess.run(['aconnect', mfrom, mto])
    except subprocess.calledProcessError:
        pass

mainapp = HeadlessSynth()
