#!/usr/bin/python3
"""
Copyright (c) 2020 Bill Peterson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

"""
Description: an implementation of patcher.py for a Raspberry Pi in a stompbox
"""
import sys, os, re, glob, subprocess
import stompboxpi as SB, patcher

def alsamidi_reconnect():
    # hack needed for old versions of fluidsynth
    x = re.search(b"client (\d+:) 'FLUID Synth", subprocess.check_output(['aconnect', '-o']))
    if not x:
        raise patcher.PatcherError("Fluid MIDI port not found")
    fluid_port = x.group(1).decode() + '0'
    for client in subprocess.check_output(['aconnect', '-i']).split(b'client'):
        x = re.match(b" (\d+:) '([ \w]*)'", client)
        if not x: continue
        if x.group(2) == b'System': continue
        if x.group(2) == b'Midi Through': continue
        for n in re.findall(b"\n +(\d+) '", client):
            client_port = x.group(1) + n
            subprocess.run(['aconnect', client_port, fluid_port]) 

def load_bank_menu():
    sb.lcd_write("Load Bank:      ", row=0)
    bpaths = sorted(glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
    if not bpaths:
        sb.lcd_write("no banks found! ", 1)
        sb.waitforrelease(2)
        return False
    banks = [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]
    i = sb.choose_opt(banks, row=1, scroll=True)
    if i < 0: return False
    sb.lcd_write("loading patches ", 1)
    try:
        pxr.load_bank(banks[i])
    except patcher.PatcherError:
        sb.lcd_write("bank load error!", 1)
        sb.waitforrelease(2)
        return False
    pxr.write_config()
    sb.waitforrelease(1)
    return True



sb = SB.StompBox()
sb.lcd_clear()
sb.lcd_write("Squishbox v3.1", 0)

# start the patcher
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = '/home/pi/SquishBox/squishboxconf.yaml'
try:
    pxr = patcher.Patcher(cfgfile)
except patcher.PatcherError:
    sb.lcd_write("bad config file!", 1)
    sys.exit("bad config file")
        
# load bank
sb.lcd_write("loading patches ", 1)
try:
    pxr.load_bank(pxr.cfg['currentbank'])
except patcher.PatcherError:
    while True:
        sb.lcd_write("bank load error!", 1)
        sb.waitfortap(10)
        if load_bank_menu():
            break
pno = 0
pxr.select_patch(pno)
alsamidi_reconnect()


# update LCD
while True:
    sb.lcd_clear()
    if pxr.sfpresets:
        ptot = len(pxr.sfpresets)
        sb.lcd_write(pxr.sfpresets[pno][0], scroll=True)
        sb.lcd_write("%16s" % ("preset %03d:%03d" % pxr.sfpresets[pno][1:3]), 1)
    else:
        ptot = pxr.patches_count()
        patchname = pxr.patch_name(pno)
        sb.lcd_write(patchname, scroll=True)
        sb.lcd_write("%16s" % ("patch: %d/%d" % (pno + 1, ptot)), 1)

    # input loop
    while True:
        sb.update()
        if sum(sb.state.values()) == SB.STATE_NONE:
            continue

        # patch/preset switching
        if SB.STATE_TAP in sb.state.values():
            if sb.state[SB.BTN_R] == SB.STATE_TAP:
                pno = (pno + 1) % ptot
            elif sb.state[SB.BTN_L] == SB.STATE_TAP:
                pno = (pno - 1) % ptot
            if pxr.sfpresets:
                pxr.select_sfpreset(pno)
            else:
                pxr.select_patch(pno)
            break

        # right button menu
        if sb.state[SB.BTN_R] == SB.STATE_HOLD:
            k = sb.choose_opt(['Save Patch', 'Delete Patch', 'Load Bank', 'Save Bank', 'Load Soundfont', 'Effects..'], row=1, passlong=True)
            
            if k == 0: # save the current patch or save preset to a patch
                sb.lcd_write("Save patch:     ", row=0)
                if pxr.sfpresets:
                    newname = sb.char_input(pxr.sfpresets[pno][0])
                    if newname == '': break
                    pxr.add_patch(newname)
                    pxr.update_patch(newname)
                else:
                    newname = sb.char_input(patchname)
                    if newname == '': break
                    if newname != patchname:
                        pxr.add_patch(newname, addlike=patchname)
                    pxr.update_patch(newname)
                pno = pxr.patch_index(newname)
                pxr.select_patch(pno)
                
            elif k == 1: # delete patch if it's not last one or a preset; ask confirm
                if pxr.sfpresets or ptot < 2:
                    sb.lcd_write("cannot delete   ", 1)
                    sb.waitforrelease(1)
                    break
                j = sb.choose_opt(['confirm delete?', 'cancel'], row=1)
                if j == 0:
                    pxr.delete_patch(patchname)
                    pno = min(pno, (ptot - 2))
                    pxr.select_patch(pno)
                    
            elif k == 2: # load bank
                if not load_bank_menu(): break
                pno = 0
                pxr.select_patch(pno)
                
            elif k == 3: # save bank, prompt for name
                if pxr.sfpresets:
                    sb.lcd_write("cannot save     ", 1)
                    sb.waitforrelease(1)
                    break
                sb.lcd_write("Save bank:       ", 0)
                bankfile = sb.char_input(pxr.cfg['currentbank'])
                if bankfile == '': break
                try:
                    pxr.save_bank(bankfile)
                except patcher.PatcherError:
                    sb.lcd_write("bank save error!", 1)
                    sb.waitforrelease(2)
                    break
                pxr.write_config()
                sb.lcd_write("bank saved.      ", 1)
                sb.waitforrelease(1)
                
            elif k == 4: # load soundfont
                sfpaths = sorted(glob.glob(os.path.join(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
                if not sfpaths:
                    sb.lcd_write("no soundfonts!  ", 1)
                    sb.waitforrelease(2)
                    break
                sf = [os.path.relpath(x, start=pxr.sfdir) for x in sfpaths]
                sb.lcd_write("Load Soundfont: ", row=0)
                s = sb.choose_opt(sf, row=1, scroll=True)
                if s < 0: break
                sb.lcd_write("loading...      ", row=1)
                pxr.load_soundfont(sfpaths[s])
                sb.waitforrelease(1)
                pno = 0
                pxr.select_sfpreset(pno)
                
            elif k == 5: # effects menu
                sb.lcd_write("Effects:        ", row=0)
                j = sb.choose_opt(['Reverb', 'Chorus', 'Gain'], 1)
                if j == 0:
                    while True:
                        sb.lcd_write("Reverb:         ", row=0)
                        i = sb.choose_opt(['Reverb Size', 'Reverb Damping','Reverb Width','Reverb Level'], 1)
                        if i < 0: break
                        if i == 0:
                            sb.lcd_write("Size (0-1):     ", row=0)
                            pxr.set_reverb(roomsize=sb.choose_val(pxr.get_reverb(roomsize=True)[0], 0.1, 0.0, 1.0, '%16.1f'))
                        elif i == 1:
                            sb.lcd_write("Damping (0-1):  ", row=0)
                            pxr.set_reverb(damp=sb.choose_val(pxr.get_reverb(damp=True)[0], 0.1, 0.0, 1.0, '%16.1f'))
                        elif i == 2:
                            sb.lcd_write("Width (0-100):  ", row=0)
                            pxr.set_reverb(width=sb.choose_val(pxr.get_reverb(width=True)[0], 1.0, 0.0, 100.0, '%16.1f'))
                        elif i == 3:
                            sb.lcd_write("Level (0-1):    ", row=0)
                            pxr.set_reverb(level=sb.choose_val(pxr.get_reverb(level=True)[0], 0.01, 0.00, 1.00, '%16.2f'))
                elif j == 1:
                    while True:
                        sb.lcd_write("Chorus:         ", row=0)
                        i = sb.choose_opt(['Chorus Voices', 'Chorus Level', 'Chorus Speed', 'Chorus Depth'], 1)
                        if i < 0: break
                        if i == 0:
                            sb.lcd_write("Voices (0-99):  ", row=0)
                            pxr.set_chorus(nr=sb.choose_val(pxr.get_chorus(nr=True)[0], 1, 0, 99,'%16d'))
                        if i == 1:
                            sb.lcd_write("Level (0-10):   ", row=0)
                            pxr.set_chorus(level=sb.choose_val(pxr.get_chorus(level=True)[0], 0.1, 0.0, 10.0, '%16.1f'))
                        if i == 2:
                            sb.lcd_write("Speed (0.1-21): ", row=0)
                            pxr.set_chorus(speed=sb.choose_val(pxr.get_chorus(speed=True)[0], 0.1, 0.1, 21.0, '%16.1f'))
                        if i == 3:
                            sb.lcd_write("Depth (0.3-5):  ", row=0)
                            pxr.set_chorus(depth=sb.choose_val(pxr.get_chorus(depth=True)[0], 0.1, 0.3, 5.0, '%16.1f'))
                elif j == 2:
                    sb.lcd_write("Gain:           ", row=0)
                    pxr.set_gain(sb.choose_val(pxr.get_gain(), 0.1, 0.0, 5.0, "%16.2f"))
            break

            
        # left button menu - system-related tasks
        if sb.state[SB.BTN_L] == SB.STATE_HOLD:
            sb.lcd_write("Options:       ", 0)
            k = sb.choose_opt(['Power Down', 'MIDI Reconnect', 'Wifi Settings', 'Add From USB'], row=1, passlong=True)
            
            if k == 0: # power down
                sb.lcd_write("Shutting down...Wait 30s, unplug", 0)
                subprocess.run('sudo shutdown -h now'.split())
                
            elif k == 1: # reconnect midi devices
                sb.lcd_write("reconnecting..  ", 1)
                alsamidi_reconnect()
                sb.waitforrelease(1)
                
            elif k == 2: # wifi settings
                ssid = subprocess.check_output(['iwgetid', 'wlan0', '--raw']).strip().decode('ascii')
                ip = re.sub(b'\s.*', b'', subprocess.check_output(['hostname', '-I'])).decode('ascii')
                if ssid == "":
                    statusmsg="Not connected   " + ' ' * 16
                else:
                    statusmsg="%16s%-16s" % (ssid,ip)
                j = sb.choose_opt([statusmsg, "Add Network..   " + ' ' * 16])
                if j != 1: break
                sb.lcd_write("Network (SSID):")
                newssid = sb.char_input()
                if not newssid: break
                sb.lcd_write("Password:")
                newpsk = sb.char_input()
                if not newpsk: break
                sb.lcd_write("adding network.." + ' ' * 16)
                f = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a')
                f.write('network={\n  ssid="%s"\n  psk="%s"\n}\n' % (newssid, newpsk))
                f.close()
                subprocess.run('sudo service networking restart'.split())
                sb.waitforrelease(1)
                
            elif k == 3: # add soundfonts from a flash drive
                sb.lcd_clear()
                sb.lcd_write("looking for USB ", row=0)
                b = subprocess.check_output('sudo blkid'.split())
                x = re.findall('/dev/sd[a-z]\d*', b.decode('ascii'))
                if not x:
                    sb.lcd_write("USB not found!  ", row=1)
                    sb.waitforrelease(1)
                    break
                sb.lcd_write("copying files.. ", row=1)
                try:
                    if not os.path.exists('/mnt/usbdrv/'):
                        os.mkdir('/mnt/usbdrv')
                    for usb in x:
                        subprocess.run(['sudo', 'mount', usb, '/mnt/usbdrv/'])
                        for sf in glob.glob(os.path.join('/mnt/usbdrv', '**', '*.sf2'), recursive=True):
                            sfrel = os.path.relpath(sf, start='/mnt/usbdrv')
                            dest = os.path.join(pxr.sfdir, sfrel)
                            if not os.path.exists(os.path.dirname(dest)):
                                os.makedirs(os.path.dirname(dest))
                            subprocess.run(['sudo', 'cp', '-f', sf, dest])
                        subprocess.run(['sudo', 'umount', usb])
                except Exception as e:
                    sb.lcd_write("halted - errors:", 0)
                    sb.lcd_write(str(e).replace('\n', ' '), 1, scroll=True)
                    while not sb.waitfortap(10):
                        pass
                sb.lcd_write("copying files.. done!           ")
                sb.waitforrelease(1)
            break

        # long-hold right button = refresh bank
        if sb.state[SB.BTN_R] == SB.STATE_LONG:
            sb.lcd_clear()
            sb.lcd_blink("Refreshing Bank ", row=0)
            lastpatch = pxr.patch_name(pno)
            pxr.load_bank(pxr.cfg['currentbank'])
            try:
                pno = pxr.patch_index(lastpatch)
            except patcher.PatcherError:
                if pno >= pxr.patches_count():
                    pno = 0
            pxr.select_patch(pno)
            sb.waitforrelease(1)
            break

        # long-hold left button = panic
        if sb.state[SB.BTN_L] == SB.STATE_LONG:
            sb.lcd_clear()
            sb.lcd_blink("Panic Restart   ", row=0)
            sb.waitforrelease(1)
            sys.exit(1)
            

