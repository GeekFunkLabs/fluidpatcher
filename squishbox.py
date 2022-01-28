#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a Raspberry Pi in a stompbox
"""
import re, sys, os, subprocess, shutil, tempfile
from pathlib import Path
import patcher
from utils import stompboxpi as SB

BUTTON_MIDICHANNEL = 16
BUTTON_MOM_CC = 30
BUTTON_TOG_CC = 31


def wifi_settings():
    x = re.search("SSID: ([^\n]+)", subprocess.check_output('iw dev wlan0 link'.split()).decode())
    ssid = x[1] if x else "Not connected"
    ip = subprocess.check_output(['hostname', '-I']).decode().strip()
    sb.lcd_clear()
    sb.lcd_write(ssid, 0)
    sb.lcd_write(ip, 1, rjust=True)
    if not sb.waitfortap(10): return
    while True:
        sb.lcd_write("Connections:", 0)
        opts = [*networks, 'Rescan..']
        j = sb.choose_opt(opts, row=1, scroll=True, timeout=0)
        if j < 0: return
        elif j == len(opts) - 1:
            sb.lcd_write("scanning ", 1, rjust=True, now=True)
            sb.progresswheel_start()
            x = subprocess.check_output('sudo iw wlan0 scan'.split()).decode()
            sb.progresswheel_stop()
            networks[:] = [s for s in re.findall('SSID: ([^\n]*)', x) if s]
        else:
            sb.lcd_write("Password:", 0)
            newpsk = sb.char_input(charset = SB.PRNCHARS)
            if newpsk == '': return
            sb.lcd_clear()
            sb.lcd_write(networks[j], 0)
            sb.lcd_write("adding network ", 1, rjust=True, now=True)
            sb.progresswheel_start()
            e = subprocess.Popen(('echo', f'network={{\n  ssid="{networks[j]}"\n  psk="{newpsk}"\n}}\n'), stdout=subprocess.PIPE)
            subprocess.run(('sudo', 'tee', '-a', '/etc/wpa_supplicant/wpa_supplicant.conf'), stdin=e.stdout, stdout=subprocess.DEVNULL)
            subprocess.run('sudo systemctl restart dhcpcd'.split())
            sb.progresswheel_stop()
            wifi_settings()
            return

def addfrom_usb():
    sb.lcd_clear()
    b = subprocess.check_output(['sudo', 'blkid']).decode()
    x = re.findall('/dev/sd[a-z]\d*', b)
    if not x:
        sb.lcd_write("USB not found", 0)
        sb.waitfortap(2)
        return
    sb.lcd_write("USB drive found", 0)
    sb.lcd_write("copying files ", 1, rjust=True, now=True)
    sb.progresswheel_start()
    try:
        subprocess.run(['sudo', 'mkdir', '-p', '/mnt/usbdrv'])
        for usb in x:
            subprocess.run(['sudo', 'mount', usb, '/mnt/usbdrv/'], timeout=30)
            for src in Path('/mnt/usbdrv/SquishBox').rglob('*'):
                if not src.is_file(): continue
                dest = 'SquishBox' / src.relative_to('/mnt/usbdrv/SquishBox')
                if not dest.parent.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            subprocess.run(['sudo', 'umount', usb], timeout=30)
    except Exception as e:
        sb.progresswheel_stop()
        sb.lcd_write(f"halted - errors: {exceptstr(e)}", 1, scroll=True)
        sb.waitfortap()
    else:
        sb.progresswheel_stop()

def update_device():
    sb.lcd_write(f"version {patcher.VERSION}", 0, scroll=True)
    sb.lcd_write("checking ", 1, rjust=True, now=True)
    sb.progresswheel_start()
    x = subprocess.check_output(['curl', 'https://raw.githubusercontent.com/albedozero/fluidpatcher/master/patcher/__init__.py'])
    newver = re.search("VERSION = '([0-9\.]+)'", x.decode())[1]
    subprocess.run(['sudo', 'apt-get', 'update'])
    u = subprocess.check_output(['sudo', 'apt-get', 'upgrade', '-sy'])
    sb.progresswheel_stop()
    fup, sysup = 0, 0
    if newver.split('.') > patcher.VERSION.split('.'):
        fup = sb.confirm_choice(f"install {newver}", row=1, timeout=0)
    else:
        sb.lcd_write("Up to date", 1, rjust=True)
        sb.waitfortap()
    if not re.search('0 upgraded, 0 newly installed', u.decode()):
        sb.lcd_write("OS out of date", 0)
        sysup = sb.confirm_choice("upgrade OS", row=1, timeout=0)
    if not (fup or sysup):
        return
    sb.lcd_write("please wait", 0)
    sb.lcd_write("updating ", 1, rjust=True, now=True)
    sb.progresswheel_start()
    try:
        if fup:
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run(['git', 'clone', 'https://github.com/albedozero/fluidpatcher', tmp])
                for src in Path(tmp).rglob('*'):
                    if not src.is_file(): continue
                    if src.suffix == ".yaml": continue
                    if src.name == "hw_overlay.py": continue
                    dest = Path.cwd() / src.relative_to(tmp)
                    if not dest.parent.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
        if sysup:
            subprocess.run(['sudo', 'apt-get', 'upgrade', '-y'])
        sb.progresswheel_stop()
        sb.lcd_write("rebooting", 1, rjust=True, now=True)
        subprocess.run(['sudo', 'reboot'])
    except Exception as e:
        sb.progresswheel_stop()
        sb.lcd_write(f"halted - errors: {exceptstr(e)}", 1, scroll=True)
        sb.waitfortap()

def exceptstr(e):
    x = re.sub('\n|\^', ' ', str(e))
    return re.sub(' {2,}', ' ', x)


class SquishBox:

    def __init__(self):
        self.pno = 0
        self.togglestate = 0
        pxr.set_midimessage_callback(self.listener)
        sb.buttoncallback = self.handle_buttonevent
        if not (pxr.currentbank and self.load_bank(pxr.currentbank)):
            while not self.load_bank(): pass
        self.patchmode()

    def listener(self, msg):
        if hasattr(msg, 'val'):
            if hasattr(msg, 'patch') and pxr.patches:
                if msg.patch == 'select':
                    self.pno = int(msg.val)
                elif msg.val > 0:
                    self.pno = (self.pno + msg.patch) % len(pxr.patches)
            elif hasattr(msg, 'gpio'):
                if msg.gpio == 'led':
                    self.togglestate = 1 if msg.val else 0
                    sb.statusled_set(self.togglestate)
            elif hasattr(msg, 'lcdwrite'):
                if hasattr(msg, 'format'):
                    val = format(msg.val, msg.format)
                    self.patchdisplay[1] = f"{msg.lcdwrite} {val}"
                else:
                    self.patchdisplay[1] = msg.lcdwrite
        else:
            self.lastmsg = msg

    def handle_buttonevent(self, button, val):
        pxr.send_event(f"cc:{BUTTON_MIDICHANNEL}:{BUTTON_MOM_CC}:{val}")
        if val:
            self.togglestate ^= 1
            pxr.send_event(f"cc:{BUTTON_MIDICHANNEL}:{BUTTON_TOG_CC}:{self.togglestate}")
            sb.statusled_set(self.togglestate)

    def patchmode(self):
        pno = -1
        while True:
            sb.lcd_clear()
            if self.pno != pno:
                if pxr.patches:
                    pno = self.pno
                    self.patchdisplay = [pxr.patches[pno], f"patch: {pno + 1}/{len(pxr.patches)}"]
                    warn = pxr.apply_patch(pno)
                else:
                    pno, self.pno = 0, 0
                    self.patchdisplay = ["No patches", "patch 0/0"]
                    warn = pxr.apply_patch(None)
                if warn:
                    sb.lcd_write(self.patchdisplay[0], 0, scroll=True)
                    sb.lcd_write('; '.join(warn), 1, scroll=True)
                    sb.waitfortap()
            display = self.patchdisplay[:]
            sb.lcd_write(display[0], 0, scroll=True)
            sb.lcd_write(display[1], 1, rjust=True)
            while True:
                if self.pno != pno: break
                if self.patchdisplay != display: break
                event = sb.update()
                if event == SB.RIGHT and pxr.patches:
                    self.pno = (self.pno + 1) % len(pxr.patches)
                elif event == SB.LEFT and pxr.patches:
                    self.pno = (self.pno - 1) % len(pxr.patches)
                elif event == SB.SELECT:
                    k = sb.choose_opt(['Load Bank', 'Save Bank', 'Save Patch', 'Delete Patch',
                                       'Open Soundfont', 'Effects..', 'System Menu..'], row=1)
                    if k == 0:
                        if self.load_bank(): pno = -1
                    elif k == 1:
                        self.save_bank()
                    elif k == 2:
                        sb.lcd_write("Save patch:", 0)
                        newname = sb.char_input(pxr.patches[self.pno])
                        if newname != '':
                            if newname != pxr.patches[self.pno]:
                                pxr.add_patch(newname, addlike=self.pno)
                            pxr.update_patch(newname)
                            self.pno = pxr.patches.index(newname)
                    elif k == 3:
                        if sb.confirm_choice('Delete', row=1):
                            pxr.delete_patch(self.pno)
                            self.pno = min(self.pno, len(pxr.patches) - 1)
                    elif k == 4:
                        if self.load_soundfont():
                            self.sfmode()
                            pno = -1
                    elif k == 5:
                        self.effects_menu()
                    elif k == 6:
                        self.system_menu()
                elif event == SB.ESCAPE:
                    if sb.confirm_choice("Reset"): sys.exit(1)
                else: continue
                break

    def sfmode(self):
        i = 0
        warn = pxr.select_sfpreset(i)
        while True:
            p = pxr.sfpresets[i]
            sb.lcd_clear()
            sb.lcd_write(p.name, 0, scroll=True)
            if warn:
                sb.lcd_write('; '.join(warn), 1, scroll=True)
                sb.waitfortap()
                warn = []
            sb.lcd_write(f"preset {p.bank:03}:{p.prog:03}", 1, rjust=True)
            while True:
                event = sb.update()
                if event == SB.RIGHT:
                    i = (i + 1) % len(pxr.sfpresets)
                    warn = pxr.select_sfpreset(i)
                elif event == SB.LEFT:
                    i = (i - 1) % len(pxr.sfpresets)
                    warn = pxr.select_sfpreset(i)
                elif event == SB.SELECT:
                    k = sb.choose_opt(['Add as Patch', 'Open Soundfont', 'Load Bank'], row=1)
                    if k == 0:
                        sb.lcd_write("Add as Patch:", 0)
                        newname = sb.char_input(p.name)
                        if newname == '': break
                        self.pno = pxr.add_patch(newname)
                        pxr.update_patch(newname)
                    elif k == 1:
                        if self.load_soundfont():
                            i = 0
                            warn = pxr.select_sfpreset(i)
                    elif k == 2:
                        if self.load_bank(): return
                elif event == SB.ESCAPE:
                    sb.lcd_clear()
                    pxr.load_bank()
                    return
                else: continue
                break

    def load_bank(self, bank=''):
        lastbank = pxr.currentbank
        lastpatch = pxr.patches[self.pno] if pxr.patches else ''
        if bank == '':
            sb.lcd_write("Load Bank:", 0)
            if not pxr.banks:
                sb.lcd_write("no banks found", 1)
                sb.waitfortap(2)
                return False
            bno = 0
            if pxr.currentbank in pxr.banks:
                bno = pxr.banks.index(pxr.currentbank)
            i = sb.choose_opt([str(b) for b in pxr.banks], bno, row=1, scroll=True, timeout=0)
            if i < 0: return False
            bank = pxr.banks[i]
        sb.lcd_write("loading patches ", 1, now=True)
        sb.progresswheel_start()
        try: pxr.load_bank(bank)
        except Exception as e:
            sb.progresswheel_stop()
            sb.lcd_write(f"bank load error: {exceptstr(e)}", 1, scroll=True)
            sb.waitfortap()
            return False
        sb.progresswheel_stop()
        pxr.write_config()
        if pxr.currentbank != lastbank:
            self.pno = 0
        else:
            if lastpatch in pxr.patches:
                self.pno = pxr.patches.index(lastpatch)
            elif self.pno >= len(pxr.patches):
                self.pno = 0
        return True

    def save_bank(self, bank=''):
        if bank == '':
            sb.lcd_write("Save bank:", 0)
            bank = sb.char_input(str(pxr.currentbank))
            if bank == '': return
        try: pxr.save_bank(bank)
        except Exception as e:
            sb.lcd_write(f"bank save error: {exceptstr(e)}", 1, scroll=True)
            sb.waitfortap()
        else:
            pxr.write_config()
            sb.lcd_write("bank saved", 1)
            sb.waitfortap(2)

    def load_soundfont(self, sfont=''):
        if sfont == '':
            sb.lcd_write("Open Soundfont:", 0)
            if not pxr.soundfonts:
                sb.lcd_write("no soundfonts", 1)
                sb.waitfortap(2)
                return False
            s = sb.choose_opt([str(sf) for sf in pxr.soundfonts], row=1, scroll=True, timeout=0)
            if s < 0: return False
            sfont = pxr.soundfonts[s]
        sb.lcd_write("loading presets ", 1, now=True)
        sb.progresswheel_start()
        if not pxr.load_soundfont(pxr.soundfonts[s]):
            sb.progresswheel_stop()
            sb.lcd_write(f"Unable to load {str(pxr.soundfonts[s])}", 1, scroll=True)
            sb.waitfortap()
            return False
        sb.progresswheel_stop()
        return True

    def effects_menu(self):
        i=0
        fxmenu_info = (
# Name             fluidsetting              inc    min     max   format
('Reverb Size',   'synth.reverb.room-size',  0.1,   0.0,    1.0, '4.1f'),
('Reverb Damp',   'synth.reverb.damp',       0.1,   0.0,    1.0, '4.1f'),
('Rev. Width',    'synth.reverb.width',      0.5,   0.0,  100.0, '5.1f'),
('Rev. Level',    'synth.reverb.level',     0.01,  0.00,   1.00, '5.2f'),
('Chorus Voices', 'synth.chorus.nr',           1,     0,     99, '2d'),
('Chor. Level',   'synth.chorus.level',      0.1,   0.0,   10.0, '4.1f'),
('Chor. Speed',   'synth.chorus.speed',      0.1,   0.1,   21.0, '4.1f'),
('Chorus Depth',  'synth.chorus.depth',      0.1,   0.3,    5.0, '3.1f'),
('Gain',          'synth.gain',              0.1,   0.0,    5.0, '11.1f'))
        vals = [pxr.fluid_get(info[1]) for info in fxmenu_info]
        fxopts = [fxmenu_info[i][0] + ':' + format(vals[i], fxmenu_info[i][5]) for i in range(len(fxmenu_info))]
        while True:
            sb.lcd_write("Effects:", 0)
            i = sb.choose_opt(fxopts, i, row=1)
            if i < 0:
                break
            sb.lcd_write(fxopts[i], 0)
            newval = sb.choose_val(vals[i], *fxmenu_info[i][2:])
            if newval != None:
                pxr.fluid_set(fxmenu_info[i][1], newval, updatebank=True, patch=self.pno)
                vals[i] = newval
                fxopts[i] = fxmenu_info[i][0] + ':' + format(newval, fxmenu_info[i][5])

    def system_menu(self):
        sb.lcd_write("System Menu:", 0)
        k = sb.choose_opt(['Power Down', 'MIDI Devices', 'Wifi Settings', 'Add From USB', 'Update Device'], row=1)
        if k == 0:
            sb.lcd_write("Shutting down..", 0)
            sb.lcd_write("Wait 30s, unplug", 1, now=True)
            subprocess.run('sudo shutdown -h now'.split())            
        elif k == 1: self.midi_devices()
        elif k == 2: wifi_settings()
        elif k == 3: addfrom_usb()
        elif k == 4: update_device()

    def midi_devices(self):
        sb.lcd_write("MIDI Devices:", 0)
        readable = re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-i']).decode())
        rports, names = list(zip(*readable))
        p = sb.choose_opt([*names, "MIDI monitor.."], row=1, scroll=True, timeout=0)
        if p < 0: return
        if 0 <= p < len(rports):
            sb.lcd_write("Connect to:", 0)
            writable = re.findall(" (\d+): '([^\n]*)'", subprocess.check_output(['aconnect', '-o']).decode())
            wports, names = list(zip(*writable))
            op = sb.choose_opt(names, row=1, scroll=True, timeout=0)
            if op < 0: return
            subprocess.run(['aconnect', rports[p], wports[op]])
        elif p == len(rports):
            sb.lcd_clear()
            sb.lcd_write("MIDI monitor:", 0)
            msg = self.lastmsg
            while not sb.waitfortap(0.1):
                if msg == self.lastmsg: continue
                msg = self.lastmsg
                t = ('note', 'noteoff', 'cc', 'kpress', 'prog', 'pbend', 'cpress').index(msg.type)
                x = ("note", "noff", "  cc", "keyp", " prog", "pbend", "press")[t]
                if t < 4:
                    sb.lcd_write(f"ch{msg.chan + 1:<3}{x}{msg.par1:3}={msg.par2:<3}", 1)
                else:
                    sb.lcd_write(f"ch{msg.chan + 1:<3}{x}={msg.par1:<5}", 1)


sb = SB.StompBox()
sb.lcd_clear()
sb.lcd_write(f"version {patcher.VERSION}", 0, now=True)

cfgfile = sys.argv[1] if len(sys.argv) > 1 else '/home/pi/SquishBox/squishboxconf.yaml'
try: pxr = patcher.Patcher(cfgfile)
except Exception as e:
    sb.lcd_write(f"bad config file {exceptstr(e)}", 1, scroll=True)
    sys.exit("bad config file")

os.umask(0o002)
networks = []

mainapp = SquishBox()
