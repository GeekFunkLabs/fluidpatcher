#!/usr/bin/env python3
"""A command-line FluidPatcher synth
"""
from pathlib import Path
import subprocess
import sys
import time

from fluidpatcher import FluidPatcher

try:
    import atexit
    import select
    import sys
    import termios
    EDITOR = 'vi'
    stdin_fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(stdin_fd)
    new_term = termios.tcgetattr(stdin_fd)
    new_term[3] = (new_term[3] & ~termios.ICANON & ~termios.ECHO)
    termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, new_term)
    def restoreterm():
        termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, old_term)
    def pollkeyb():
        dr,dw,de = select.select([sys.stdin], [], [], 0)
        if not dr == []:
            return sys.stdin.read(1)
        return None
    atexit.register(restoreterm)
except ImportError:
    import msvcrt
    EDITOR = 'notepad'
    def pollkeyb():
        if msvcrt.kbhit():
            return msvcrt.getch().decode()
        return None

MENU = "Options: N)ext Patch P)rev Patch L)oad Next Bank M)idi Monitor E)dit Bank Q)uit"
POLL_TIME = 0.025
MSG_TYPES = 'note', 'noteoff', 'kpress', 'cc', 'prog', 'pbend', 'cpress'
MSG_NAMES = "Note On", "Note Off", "Key Pressure", "Control Change", "Program Change", "Pitch Bend", "Aftertouch"
s = type('State', (), dict(pno=0, monitor=False))

def load_bank(bfile):
    lastbank = fp.currentbank
    lastpatch = fp.patches[s.pno] if fp.patches else ""
    print(f"Loading bank '{bfile}' .. ", end="")
    try:
        fp.load_bank(bfile)
    except Exception as e:
        print(f"failed\n{str(e)}")
        sys.exit()
    print("done")
    fp.write_config()
    if fp.currentbank == lastbank and lastpatch in fp.patches:
        s.pno = fp.patches.index(lastpatch)
    else:
        s.pno = 0
    fp.apply_patch(s.pno)
    print(f"Selected patch {s.pno + 1}/{len(fp.patches)}: {fp.patches[s.pno]}")            

def sig_handler(sig):
    if hasattr(sig, 'patch'):
        if sig.patch == -1:
            s.pno = (s.pno + sig.val) % len(fp.patches)
        else:
            s.pno = sig.patch
        fp.apply_patch(s.pno)
        print(f"Selected patch {s.pno + 1}/{len(fp.patches)}: {fp.patches[s.pno]}")            
    elif s.monitor and not hasattr(sig, 'val'):
        t = MSG_TYPES.index(sig.type)
        if t < 3:
            octave = int(sig.par1 / 12) - 1
            note = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')[sig.par1 % 12]
            print(f"{MSG_NAMES[t]:15} : Channel {sig.chan:2} : {sig.par1} ({note}{octave})={sig.par2}")
        elif t < 4:
            print(f"{MSG_NAMES[t]:15} : Channel {sig.chan:2} : {sig.par1}={sig.par2}")
        elif t < 7:
            print(f"{MSG_NAMES[t]:15} : Channel {sig.chan:2} : {sig.par1}")

cfgfile = sys.argv[1] if len(sys.argv) > 1 else 'config/fluidpatcherconf.yaml'
try:
    fp = FluidPatcher(cfgfile)
except Exception as e:
    print(f"Error loading config file {cfgfile}\n{str(e)}")
    sys.exit()
fp.midi_callback = sig_handler
load_bank(fp.currentbank)
print(MENU)
while True:
    if c := pollkeyb():
        if c in 'np':
            if c == 'n':
                s.pno = (s.pno + 1) % len(fp.patches)
            elif c == 'p':
                s.pno = (s.pno - 1) % len(fp.patches)
            fp.apply_patch(s.pno)
            print(f"Selected patch {s.pno + 1}/{len(fp.patches)}: {fp.patches[s.pno]}")
        elif c == 'l':
            banks = sorted([b.relative_to(fp.bankdir)
                           for b in fp.bankdir.rglob('*.yaml')])
            if fp.currentbank in banks:
                bno = (banks.index(fp.currentbank) + 1) % len(banks)
            else:
                bno = 0
            load_bank(banks[bno])
        elif c == 'm':
            s.monitor = False if s.monitor else True
        elif c == 'e':
            subprocess.run([EDITOR, fp.bankdir / fp.currentbank])
            load_bank(fp.currentbank)
        elif c == 'q':
            sys.exit()
        else:
            print(MENU)
    time.sleep(POLL_TIME)
