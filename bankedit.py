#!/usr/bin/python3
"""
Copyright (c) 2020 Bill Peterson

Description: a curses-based implementation of patcher.py for live editing/playing of bank files
"""
import os, sys, glob, re, curses
from subprocess import call, check_output
import patcher

def padline(msg, width):
    if width > len(msg): msg += " " * (width - len(msg) - 1)
    return msg[0:width - 1]

def alsamidi_reconnect():
    x = re.search(b"client (\d+:) 'FLUID Synth", check_output(['aconnect', '-o']))
    if not x:
        raise patcher.PatcherError("Fluid MIDI port not found")
    fluid_port = x.group(1).decode() + '0'
    for client in check_output(['aconnect', '-i']).split(b'client'):
        x = re.match(b" (\d+:) '([ \w]*)'", client)
        if not x: continue
        if x.group(2) == b'System': continue
        if x.group(2) == b'Midi Through': continue
        for n in re.findall(b"\n +(\d+) '", client):
            client_port = x.group(1) + n
            call(['aconnect', client_port, fluid_port]) 

def choosefile_menu(screen, files, title="File: ", name=""):

    height, width = screen.getmaxyx()
    tentry = curses.newwin(0, width, 0, 0)
    filescr = curses.newpad(len(files), width)
    filescr.addstr(0, 0, '\n'.join(files))
    footbar = curses.newwin(1, width)

    if name == "":
        name = files[0]
    n = 0
    nlast = 0
    screen.move(1, 0)
    
    while True:
        height, width = screen.getmaxyx()
        ntop = max(n - height + 3, 0)

        tentry.addstr(0, 0, padline(title + name, width), curses.color_pair(1))
        footbar.addstr(0, 0, padline("Enter:Accept  Escape:Cancel", width), curses.color_pair(1))
        footbar.mvwin(min(len(files) + 1, height - 2), 0)
        filescr.addstr(nlast, 0, padline(files[nlast], width))
        filescr.addstr(n, 0, padline(files[n], width), curses.color_pair(1))
        screen.move(0, len(title + name))
        
        tentry.noutrefresh()
        footbar.noutrefresh()
        filescr.noutrefresh(ntop, 0, 1, 0, height - 2, width - 1)
        curses.doupdate()        

        nlast = n
        k = screen.getch()
        if k == curses.KEY_DOWN:
            n = (n + 1) % len(files)
            name = files[n]
        elif k == curses.KEY_UP:
            n = (n - 1) % len(files)
            name = files[n]
        elif k == 27: # esc
            del tentry, footbar, filescr
            screen.clear()
            screen.refresh()
            return ""
        elif k == 10: # line feed
            del tentry, footbar, filescr
            screen.clear()
            screen.refresh()
            return name
        elif k == 8 or k == 263: # backspace
            if len(name) > 0:
                name = name[0:-1]
        elif chr(k).isprintable():
            name += chr(k)
            
def soundfont_browser(screen, soundfont):

    pxr.load_soundfont(soundfont)
    pnames = ["%03d:%03d %s" % (bank, prog, name) for name, bank, prog in pxr.sfpresets]

    height, width = screen.getmaxyx()
    statusbar = curses.newwin(0, width, 0, 0)
    sfbrowser = curses.newpad(len(pnames), width)
    sfbrowser.addstr(0, 0, '\n'.join(pnames))
    footbar = curses.newwin(1, width)

    n = 0
    nlast = 0
    pxr.select_sfpreset(n)
    curses.curs_set(0)
    
    while True:
        height, width = screen.getmaxyx()
        ntop = max(n - height + 3, 0)
        
        statusbar.addstr(0, 0, padline(soundfont, width), curses.color_pair(1))
        footbar.addstr(0, 0, padline("Up/Down:choose  Escape:Close", width), curses.color_pair(1))
        footbar.mvwin(min(len(pnames) + 1, height - 1), 0)
        sfbrowser.addstr(nlast, 0, padline(pnames[nlast], width))
        sfbrowser.addstr(n, 0, padline(pnames[n], width), curses.color_pair(1))
        
        statusbar.noutrefresh()
        footbar.noutrefresh()
        sfbrowser.noutrefresh(ntop, 0, 1, 0, height - 2, width - 1)
        curses.doupdate()        

        nlast = n
        k = screen.getch()
        if k == curses.KEY_DOWN:
            n = (n + 1) % len(pnames)
            pxr.select_sfpreset(n)
        elif k == curses.KEY_UP:
            n = (n - 1) % len(pnames)
            pxr.select_sfpreset(n)
        elif k == 27: # esc
            del statusbar, footbar, sfbrowser
            screen.clear()
            screen.refresh()
            curses.curs_set(2)
            return

def main(screen):

    errormsg = ''
    rawbank = ''
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    statusbar = curses.newwin(1, 0)
    optbar = curses.newwin(1, 0)
    pad = curses.newpad(1, 1)

    while True:
        if not rawbank:
            f = open(os.path.join(pxr.bankdir, pxr.cfg['currentbank']))
            rawbank = f.read()
            f.close()
        pad.clear()
        plines = len(rawbank.splitlines()) + 1
        pwidth = max([len(x) for x in rawbank.splitlines()]) + 1
        pad.resize(plines, pwidth)
        pad.addstr(0, 0, rawbank)
        pno = 0
        ptot = len(pxr.bank['patches'])

        warn = pxr.select_patch(pno)
        if warn:
            errormsg = ', '.join(warn)
        cursor_x = 0
        cursor_y = 1
        pad_x = 0
        pad_y = 0
        k = 0
        screen.clear()
        screen.refresh()
        
        while True:
            height, width = screen.getmaxyx()

            patchname = list(pxr.bank['patches'])[pno]
            statmsg = padline("Bank: %s  Patch: %s" % (pxr.cfg['currentbank'], patchname), width)
            if errormsg:
                statmsg = padline(errormsg, width)
                errormsg = ''
            statusbar.addstr(0, 0, statmsg, curses.color_pair(1))
            statusbar.mvwin(0, 0)
            optstr = padline("PgUp/Dn:patch  F5:refresh  F6:save  F7:load  F8:soundfont  Ctrl-X:quit", width)
            optbar.addstr(0, 0, optstr, curses.color_pair(1))
            optbar.mvwin(height - 1, 0)
            screen.move(cursor_y, cursor_x)

            pad.noutrefresh(pad_y, pad_x, 1, 0, height - 2, width - 1)
            statusbar.noutrefresh()
            optbar.noutrefresh()
            curses.doupdate()
            
            k = screen.getch()

            if k == curses.KEY_DOWN:
                cursor_y = cursor_y + 1
            elif k == curses.KEY_UP:
                cursor_y = cursor_y - 1
            elif k == curses.KEY_RIGHT:
                cursor_x = cursor_x + 1
            elif k == curses.KEY_LEFT:
                cursor_x = cursor_x - 1
            elif k == curses.KEY_PPAGE:
                pno = (pno - 1) % ptot
                warn = pxr.select_patch(pno)
                if warn:
                    errormsg = ', '.join(warn)
            elif k == curses.KEY_NPAGE:
                pno = (pno + 1) % ptot
                warn = pxr.select_patch(pno)
                if warn:
                    errormsg = ', '.join(warn)
            elif k == curses.KEY_F5: # refresh the bank with what's on screen
                rawbank = '\n'.join([pad.instr(i, 0).decode().rstrip() for i in range(plines)])
                try:
                    pxr.load_bank(rawbank)
                except Exception as e:
                    errormsg = str(e).replace('\n', ' ')
                    continue
                break
            elif k == curses.KEY_F6: # save editor contents as bank
                rawbank = '\n'.join([pad.instr(i, 0).decode().rstrip() for i in range(plines)])
                try:
                    pxr.read_yaml(rawbank)
                except Exception as e:
                    errormsg = str(e).replace('\n', ' ')
                    continue
                bpaths = glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True)
                brel = [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]
                bfile = choosefile_menu(screen, brel, "Save: ", pxr.cfg['currentbank'])
                if not bfile: continue
                try:
                    pxr.save_bank(bfile, rawbank)
                except Exception as e:
                    errormsg = str(e).replace('\n', ' ')
                    continue
                break
            elif k == curses.KEY_F7: # load a new bank into editor
                bpaths = glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True)
                brel = [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]
                bfile = choosefile_menu(screen, brel, "Load: ")
                if not bfile: continue
                try:
                    pxr.load_bank(bfile)
                except Exception as e:
                    errormsg = str(e).replace('\n', ' ')
                    continue
                rawbank = ''
                break
            elif k == curses.KEY_F8: # play presets from a soundfont
                sfpaths = glob.glob(os.path.join(pxr.sfdir, '**', '*.sf2'), recursive=True)
                sf = [os.path.relpath(x, start=pxr.sfdir) for x in sfpaths]
                sfont = choosefile_menu(screen, sf, "Load Soundfont: ")
                if not sfont: continue
                soundfont_browser(screen, sfont)
                if pxr.cfg['currentbank']:
                    pxr.load_bank(pxr.cfg['currentbank'])
                break
            elif k == 24: # ctrl-X
                return
            else: # typing
                y = cursor_y + pad_y - 1
                x = cursor_x + pad_x
                if k == 8 or k == 263: # backspace
                    if x > 0:
                        pad.delch(y, x - 1)
                        cursor_x -= 1
                    elif y > 0:
                        t1 = pad.instr(y - 1, 0, pwidth).rstrip()
                        t2 = pad.instr(y, 0, pwidth).rstrip()
                        while len(t1 + t2) >= pwidth:
                            pwidth += 1
                        else:
                            pad.resize(plines, pwidth)
                        pad.deleteln()
                        pad.addstr(y - 1, 0, t1 + t2)
                        cursor_y -= 1
                        cursor_x = len(t1)
                elif k == 10: # line feed
                    t2 = pad.instr(y, x, pwidth - x).rstrip()
                    pad.insch(y, x, k)
                    plines += 1
                    pad.resize(plines, pwidth)
                    pad.move(y + 1, 0)
                    pad.insertln()
                    pad.addstr(y + 1, 0, t2)
                    cursor_y += 1
                    cursor_x = 0
                elif chr(k).isprintable():
                    pad.insch(y, x, k)
                    cursor_x += 1
                    if len(pad.instr(y, 0).rstrip()) == pwidth:
                        pwidth += 1
                    pad.resize(plines, pwidth)

            # constraints and scrolling
            if cursor_x < 0:
                cursor_x = 0
                pad_x = max(0, pad_x - 1)
            if cursor_x > min(width - 1, pwidth - 1):
                cursor_x = min(width - 1, pwidth - 1)
                pad_x = min(max(0, pwidth - width), pad_x + 1)
            if cursor_y < 1:
                cursor_y = 1
                pad_y = max(0, pad_y - 1)
            if cursor_y > min(height - 2, plines - 1):
                cursor_y = min(height - 2, plines)
                pad_y = min(max(0, plines - height + 2), pad_y + 1)




if __name__ == "__main__":

    if len(sys.argv) > 1:
        cfgfile = sys.argv[1]
    else:
        cfgfile = 'patcherconf.yaml'

    pxr = patcher.Patcher(cfgfile)

    print("Starting patcher with ", pxr.cfg['currentbank'])
    print("loading patches...")
    pxr.load_bank(pxr.cfg['currentbank'])

    try:
        alsamidi_reconnect()
    except:
        pass

    curses.wrapper(main)

