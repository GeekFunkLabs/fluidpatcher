#!/usr/bin/python3
"""
Copyright (c) 2020 Bill Peterson

Description: an implementation of patcher.py for a Raspberry Pi in a stompbox
"""
import time, sys, os, re, glob
from subprocess import call, check_output
import patcher
import stompboxpi as SB

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

def load_bank_menu():
    SB.lcd_message("Load Bank:      ", row=0)
    bpaths = sorted(glob.glob(os.path.join(pxr.bankdir, '**', '*.yaml'), recursive=True), key=str.lower)
    if not bpaths:
        SB.lcd_message("no banks found! ",1)
        SB.waitforrelease(2)
        return False
    banks = [os.path.relpath(x, start=pxr.bankdir) for x in bpaths]
    i = SB.choose_opt(banks, row=1, scroll=True)
    if i < 0: return False
    SB.lcd_message("loading patches ",1)
    try:
        pxr.load_bank(bpaths[i])
    except patcher.PatcherError:
        SB.lcd_message("bank load error!",1)
        SB.waitforrelease(2)
        return False
    pxr.write_config()
    SB.waitforrelease(1)
    return True



script_path = os.path.dirname(os.path.abspath(__file__))

SB.lcd_clear()
SB.lcd_message("Squishbox v0.3", 0)

# start the patcher
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = os.path.join(script_path, 'squishboxconf.yaml')
try:
    pxr = patcher.Patcher(cfgfile)
except patcher.PatcherError:
    while(True):
        SB.lcd_message("bad config file!", 1)
        time.sleep(10)

# load bank
SB.lcd_message("loading patches ", 1)
try:
    pxr.load_bank(os.path.join(pxr.bankdir, pxr.cfg['currentbank']))
except patcher.PatcherError:
    while True:
        SB.lcd_message("bank load error!",1)
        SB.waitfortap(10)
        if load_bank_menu():
            break
pno = 0
pxr.select_patch(pno)
alsamidi_reconnect()
SB.reset_scroll()

# main loop
while True:
    # update LCD
    time.sleep(SB.POLL_TIME)
    if pxr.sfpresets:
        ptot = len(pxr.sfpresets)
        SB.lcd_scroll(pxr.sfpresets[pno][0], 0)
        SB.lcd_message("%16s" % ("preset %03d:%03d" % pxr.sfpresets[pno][1:3]), 1)
    else:
        ptot = len(pxr.bank['patches'])
        patch_name = list(pxr.bank['patches'])[pno]
        SB.lcd_scroll(patch_name, 0)
        SB.lcd_message("%16s" % ("patch: %d/%d" % (pno + 1, ptot)), 1)
        
    # patch/preset switching
    SB.poll_stompswitches()
    if SB.r_state+SB.l_state==SB.STATE_NONE:
        continue
    if SB.r_state == SB.STATE_TAP or SB.l_state == SB.STATE_TAP:
        if SB.r_state == SB.STATE_TAP:
            pno = (pno + 1) % ptot
        elif SB.l_state == SB.STATE_TAP:
            pno = (pno - 1) % ptot
        if pxr.sfpresets:
            pxr.select_sfpreset(pno)
        else:
            pxr.select_patch(pno)
        SB.reset_scroll()
        continue

# right button menu
    if SB.r_state==SB.STATE_HOLD:
        k = SB.choose_opt(['Save Patch', 'Delete Patch', 'Load Bank', 'Save Bank', 'Load Soundfont', 'Effects..'], 1)
        
        if k == 0: # save the current patch or save preset to a patch
            SB.lcd_message("Save patch:     ", row=0)
            if pxr.sfpresets:
                newname = SB.char_input(pxr.sfpresets[pno][0])
                if newname == '': continue
                newpatch = pxr.add_patch(newname)
                pxr.update_patch(newpatch)
            else:
                newname = SB.char_input(patch_name)
                if newname == '': continue
                patch = pxr.bank['patches'][patch_name]
                if newname != patch_name:
                    patch = pxr.add_patch(newname, addlike=patch)
                pxr.update_patch(patch)
            pno = list(pxr.bank['patches']).index(newname)
            pxr.select_patch(pno)
            
        elif k == 1: # delete patch if it's not last one or a preset; ask confirm
            if pxr.sfpresets or ptot < 2:
                SB.lcd_message("cannot delete   ",1)
                SB.waitforrelease(1)
                continue
            j = SB.choose_opt(['confirm delete?', 'cancel'], row=1)
            if j == 0:
                pxr.delete_patch(patch_name)
                pno = min(pno, (ptot - 2))
                pxr.select_patch(pno)
                
        elif k == 2: # load bank
            if not load_bank_menu(): continue
            pno = 0
            pxr.select_patch(pno)
            
        elif k == 3: # save bank, prompt for name
            SB.lcd_message("Save bank:       ", 0)
            bankfile = SB.char_input(os.path.relpath(pxr.cfg['currentbank'], start=pxr.bankdir))
            try:
                pxr.save_bank(bankfile)
            except patcher.PatcherError:
                SB.lcd_message("bank save error!",1)
                SB.waitforrelease(2)
                continue
            pxr.write_config()
            SB.lcd_message("bank saved.      ", 1)
            SB.waitforrelease(1)
            
        elif k == 4: # load soundfont
            sfpaths = sorted(glob.glob(os.path.join(pxr.sfdir, '**', '*.sf2'), recursive=True), key=str.lower)
            if not sfpaths:
                SB.lcd_message("no soundfonts!  ",1)
                SB.waitforrelease(2)
                continue
            sf = [os.path.relpath(x, start=pxr.sfdir) for x in sfpaths]
            SB.lcd_message("Load Soundfont: ", row=0)
            s = SB.choose_opt(sf, row=1, scroll=True)
            if s < 0: continue
            SB.lcd_message("loading...      ", row=1)
            pxr.load_soundfont(sfpaths[s])
            SB.waitforrelease(1)
            pno = 0
            pxr.select_sfpreset(pno)
            
        elif k == 5: # effects menu
            SB.lcd_message("Effects:        ", row=0)
            j = SB.choose_opt(['Reverb', 'Chorus', 'Gain'], 1)
            if j == 0:
                while True:
                    SB.lcd_message("Reverb:         ", row=0)
                    i = SB.choose_opt(['Reverb Size', 'Reverb Damping','Reverb Width','Reverb Level'], 1)
                    if i < 0: break
                    if i == 0:
                        SB.lcd_message("Size (0-1):     ", row=0)
                        pxr.set_reverb(roomsize=SB.choose_val(pxr.get_reverb(roomsize=True)[0], 0.1, 0.0, 1.0, '%16.1f'))
                    elif i == 1:
                        SB.lcd_message("Damping (0-1):  ", row=0)
                        pxr.set_reverb(damp=SB.choose_val(pxr.get_reverb(damp=True)[0], 0.1, 0.0, 1.0, '%16.1f'))
                    elif i == 2:
                        SB.lcd_message("Width (0-100):  ", row=0)
                        pxr.set_reverb(width=SB.choose_val(pxr.get_reverb(width=True)[0], 1.0, 0.0, 100.0, '%16.1f'))
                    elif i == 3:
                        SB.lcd_message("Level (0-1):    ", row=0)
                        pxr.set_reverb(level=SB.choose_val(pxr.get_reverb(level=True)[0], 0.01, 0.00, 1.00, '%16.2f'))
            elif j == 1:
                while True:
                    SB.lcd_message("Chorus:         ", row=0)
                    i = SB.choose_opt(['Chorus Voices', 'Chorus Level', 'Chorus Speed', 'Chorus Depth'], 1)
                    if i < 0: break
                    if i == 0:
                        SB.lcd_message("Voices (0-99):  ", row=0)
                        pxr.set_chorus(nr=SB.choose_val(pxr.get_chorus(nr=True)[0], 1, 0, 99,'%16d'))
                    if i == 1:
                        SB.lcd_message("Level (0-10):   ", row=0)
                        pxr.set_chorus(level=SB.choose_val(pxr.get_chorus(level=True)[0], 0.1, 0.0, 10.0, '%16.1f'))
                    if i == 2:
                        SB.lcd_message("Speed (0.1-21): ", row=0)
                        pxr.set_chorus(speed=SB.choose_val(pxr.get_chorus(speed=True)[0], 0.1, 0.1, 21.0, '%16.1f'))
                    if i == 3:
                        SB.lcd_message("Depth (0.3-5):  ", row=0)
                        pxr.set_chorus(depth=SB.choose_val(pxr.get_chorus(depth=True)[0], 0.1, 0.3, 5.0, '%16.1f'))
            elif j == 2:
                SB.lcd_message("Gain:           ", row=0)
                pxr.set_gain(SB.choose_val(pxr.get_gain(), 0.1, 0.0, 5.0, "%16.2f"))
        continue
        
        
# left button menu - system-related tasks
    if SB.l_state==SB.STATE_HOLD:
        SB.lcd_message("Options:       ", 0)
        k = SB.choose_opt(['MIDI Reconnect', 'Power Down', 'Wifi Settings', 'Add From USB'], 1)
        
        if k == 0: # reconnect midi devices
            SB.lcd_message("reconnecting..  ", 1)
            alsamidi_reconnect()
            SB.waitforrelease(1)
            
        elif k == 1: # power down
            SB.lcd_message("Shutting down...Wait 30s, unplug", 0)
            call('sudo shutdown -h now'.split())
            
        elif k == 2: # wifi settings
            ssid=check_output(['iwgetid', 'wlan0', '--raw']).strip().decode('ascii')
            ip=re.sub(b'\s.*', b'', check_output(['hostname', '-I'])).decode('ascii')
            if ssid=="":
                statusmsg="Not connected   " + ' ' * 16
            else:
                statusmsg="%16s%-16s" % (ssid,ip)
            j=SB.choose_opt([statusmsg, "Add Network..   " + ' ' * 16])
            if j!=1: continue
            SB.lcd_message("Network (SSID):")
            newssid=SB.char_input()
            if not newssid: continue
            SB.lcd_message("Password:")
            newpsk=SB.char_input()
            if not newpsk: continue
            SB.lcd_message("adding network.." + ' ' * 16)
            f=open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a')
            f.write('network={\n  ssid="%s"\n  psk="%s"\n}\n' % (newssid,newpsk))
            f.close()
            call('sudo service networking restart'.split())
            SB.waitforrelease(1)
            
        elif k == 3: # add soundfonts from a flash drive
            SB.lcd_clear()
            SB.lcd_message("looking for USB ", row=0)
            b=check_output('sudo blkid'.split())
            x=re.findall('/dev/sd[a-z]\d*', b.decode('ascii'))
            if not x:
                SB.lcd_message("USB not found!  ", row=1)
                SB.waitforrelease(1)
                continue
            SB.lcd_message("copying files.. ", row=1)
            try:
                if not os.path.exists('/mnt/usbdrv/'):
                    os.mkdir('/mnt/usbdrv')
                for usb in x:
                    call(['sudo', 'mount', usb, '/mnt/usbdrv/'])
                    for sf in glob.glob(os.path.join('/mnt/usbdrv', '**', '*.sf2'), recursive=True):
                        sfrel = os.path.relpath(sf, start='/mnt/usbdrv')
                        dest = os.path.join(pxr.sfdir, sfrel)
                        if not os.path.exists(os.path.dirname(dest)):
                            os.makedirs(os.path.dirname(dest))
                        call(['sudo', 'cp', '-f', sf, dest])
                    call(['sudo', 'umount', usb])
            except Exception as e:
                SB.lcd_message("halted - errors:", 0)
                SB.reset_scroll()
                while not SB.waitfortap(.1):
                    SB.lcd_scroll(str(e).replace('\n', ' '), 1)
                continue
            SB.lcd_message("copying files.. done!           ")
            SB.waitforrelease(1)
