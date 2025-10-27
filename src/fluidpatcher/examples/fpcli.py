#!/usr/bin/env python3
"""A command-line FluidPatcher synth
"""
from pathlib import Path
import subprocess
import sys
import time

from fluidpatcher import FluidPatcher, CONFIG, save_state


try:
    import termios
except ImportError:
    import msvcrt
    EDITOR = 'notepad'
    def pollkeyb():
        if msvcrt.kbhit():
            return msvcrt.getch().decode('latin-1').lower()
        return None
else:
    import atexit
    import select
    EDITOR = 'vi'
    stdin_fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(stdin_fd)
    new_term = list(old_term)
    new_term[3] = (new_term[3] & ~termios.ICANON & ~termios.ECHO)
    termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, new_term)
    def restoreterm():
        termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, old_term)
    atexit.register(restoreterm)
    def pollkeyb():
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if not dr == []:
            return sys.stdin.read(1).lower()
        return None


POLL_TIME = 0.025
KEYS_INFO = "N)ext patch P)rev patch L)oad next bank M)idi debug E)dit bank Q)uit"


def load_bank(f):
    print(f"Loading bank {f} .. ", end="")
    try:
        fp.load_bank(f)
    except Exception as e:
        print()
        e.add_note(f"Unable to load {f}")
        raise
    else:
        CONFIG["current_bank"] = f
        save_state(CONFIG)
        print("done")


def choose_patch(p):
    fp.apply_patch(p)
    print(f"{bankfile} : {list(fp.bank.patches)[p]} ({p + 1}/{len(fp.bank)})")


def midi_debug(event):
    if debug_on:
        print(event)


# main
fp = FluidPatcher()

debug_on = False
fp.set_callback(midi_debug)

bankfile = fp.cfg.bankfile
load_bank(CONFIG["current_bank"])

pno = 0
choose_patch(pno)

print(KEYS_INFO)
while True:
    match pollkeyb().lower():
        case 'n':
            pno = (pno + 1) % len(fp.bank)
            choose_patch(pno)
        case 'p':
            pno = (pno - 1) % len(fp.bank)
            choose_patch(pno)
        case 'l':
            banks = sorted([b.relative_to(CONFIG["banks_path"])
                           for b in CONFIG["banks_path"].rglob('*.yaml')])
            if bankfile in banks:
                i = banks.index(bankfile) + 1
                bankfile = banks[i % len(banks)]
            else:
                bankfile = banks[0]
            load_bank(bankfile)
        case 'm':
            debug_on = False if debug_on else True
            print("Midi debug", "ON" if debug_on else "OFF")
        case 'e':
            subprocess.run([EDITOR, CONFIG["banks_path"] / CONFIG["current_bank"]])
            load_bank(bankfile)
            choose_patch(pno)
        case 'q':
            sys.exit()
        case _:
            print(KEYS_INFO)
    time.sleep(POLL_TIME)

