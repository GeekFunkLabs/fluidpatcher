#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a Raspberry Pi in a stompbox
"""
import re, sys, os, subprocess, shutil, tempfile
from pathlib import Path
from patcher import Patcher, PatcherError, VERSION
from utils import netlink, stompboxpi as SB


class SquishBox:

    def __init__(self):
        self.latest_midimessage = None
        self.networks = []
        pxr.set_midimessage_callback(self.midimessage_listener)
        # initialize network link
        if pxr.cfg.get('netlink_active', 0):
            port = pxr.cfg.get('netlink_port', netlink.DEFAULT_PORT)
            passkey = pxr.cfg.get('netlink_passkey', netlink.DEFAULT_PASSKEY)
            self.nwlink = netlink.Server(port, passkey)
        else:
            self.nwlink = None
        # load initial bank
        if not self.load_bank(pxr.currentbank):
            while True:
                sb.waitfortap(10)
                if self.load_bank(): break
                sb.lcd_write("bank load error!", 1)
        self.select_patch(0)
        self.mainloop()

    def midimessage_listener(self, msg):
        if hasattr(msg, 'val'):
            pass # handle triggers for midi/mp3 player/looper, etc.
        else:
            self.latest_midimessage = msg

    def load_bank(self, bank=''):
        if bank == '':
            sb.lcd_write("Load Bank:", 0)
            if not pxr.banks:
                sb.lcd_write("no banks found!", 1)
                sb.waitforrelease(2)
                return False
            i = sb.choose_opt([str(b) for b in pxr.banks], row=1, scroll=True, timeout=0)
            if i < 0: return False
            bank = pxr.banks[i]
        sb.lcd_write("loading patches", 1, rjust=True)
        try: rawbank = pxr.load_bank(bank)
        except PatcherError:
            sb.lcd_write("bank load error!", 1)
            sb.waitforrelease(2)
            return False
        pxr.write_config()
        sb.waitforrelease(1)
        return rawbank

    def save_bank(self, bank=''):
        if bank == '':
            sb.lcd_write("Save bank:", 0)
            bank = sb.char_input(str(pxr.currentbank))
            if bank == '': return
        try: pxr.save_bank(bank)
        except PatcherError:
            sb.lcd_write("bank save error!", 1)
        else:
            pxr.write_config()
            sb.lcd_write("bank saved.", 1)
        sb.waitforrelease(1)

    def load_soundfont(self, sfont=''):
        if sfont == '':
            sb.lcd_write("Open Soundfont:", 0)
            if not pxr.soundfonts:
                sb.lcd_write("no soundfonts!", 1)
                sb.waitforrelease(2)
                return False
            s = sb.choose_opt([str(sf) for sf in pxr.soundfonts], row=1, scroll=True, timeout=0)
            if s < 0: return False
            sfont = pxr.soundfonts[s]
        sb.lcd_write("loading...", 1, rjust=True)
        if not pxr.load_soundfont(sfont):
            sb.lcd_write("unable to load!", 1)
            sb.waitforrelease(2)
            return False
        sb.waitforrelease(1)
        return True

    def reload_bank(self):
        sb.lcd_clear()
        sb.lcd_blink("Reloading Bank", 0)
        lastpatch = pxr.patches[self.pno]
        pxr.load_bank(pxr.currentbank)
        if lastpatch in pxr.patches:
            self.select_patch(pxr.patches.index(lastpatch))
        else:
            self.select_patch(0)

    def select_patch(self, pno):
        self.pno = pno
        warn = pxr.select_patch(self.pno)
        sb.lcd_write(pxr.patches[self.pno], 0, scroll=True)
        if warn:
            sb.lcd_write('; '.join(warn), 1, scroll=True)
            sb.waitfortap()
            warn = []
        sb.lcd_write(f"patch: {self.pno + 1}/{len(pxr.patches)}", 1, rjust=True)

    def mainloop(self):
        while True:
            sb.lcd_write(pxr.patches[self.pno], 0, scroll=True)
            sb.lcd_write(f"patch: {self.pno + 1}/{len(pxr.patches)}", 1, rjust=True)
            while True:
                sb.update()
                self.netlink_poll()
                if SB.TAP in sb.buttons:
                    if sb.right == SB.TAP:
                        self.select_patch((self.pno + 1) % len(pxr.patches))
                    elif sb.left == SB.TAP:
                        self.select_patch((self.pno - 1) % len(pxr.patches))
                elif sb.right == SB.HOLD: self.patch_options()
                elif sb.left == SB.HOLD: self.system_menu()
                elif sb.right == SB.LONG: self.reload_bank()
                elif sb.left == SB.LONG: self.panic_restart()
                else: continue
                break

    def patch_options(self):
        k = sb.choose_opt(['Save Patch', 'Delete Patch', 'Load Bank', 'Save Bank', 'Open Soundfont', 'Effects..'], row=1, passlong=True)
        if k == 0: # update patch, or save as new
            sb.lcd_write("Save patch:", 0)
            newname = sb.char_input(pxr.patches[self.pno])
            if newname == '': return
            if newname != pxr.patches[self.pno]:
                pxr.add_patch(newname, addlike=self.pno)
            pxr.update_patch(newname)
            self.select_patch(pxr.patches.index(newname))
        elif k == 1: # delete patch, ask to confirm
            j = sb.choose_opt(['confirm delete?'], row=1)
            if j == 0:
                pxr.delete_patch(self.pno)
                self.pno = min(self.pno, len(pxr.patches) - 1)
                self.select_patch(min(self.pno, len(pxr.patches) - 1))
        elif k == 2:
            if self.load_bank(): self.select_patch(0)
        elif k == 3:
            self.save_bank()
        elif k == 4:
            if self.load_soundfont(): self.presetmode()
        elif k == 5: self.effects_menu()

    def presetmode(self):
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
                sb.update()
                if SB.TAP in sb.buttons:
                    if sb.right == SB.TAP: i = (i + 1) % len(pxr.sfpresets)
                    elif sb.left == SB.TAP: i = (i - 1) % len(pxr.sfpresets)
                    warn = pxr.select_sfpreset(i)
                elif sb.right == SB.HOLD:
                    k = sb.choose_opt(['Add as Patch', 'Load Bank', 'Open Soundfont'], row=1, passlong=True)
                    if k == 0:
                        sb.lcd_write("Add as Patch:", 0)
                        newname = sb.char_input(p.name)
                        if newname == '': break
                        self.pno = pxr.add_patch(newname)
                        pxr.update_patch(newname)
                    elif k == 1:
                        if self.load_bank():
                            self.select_patch(0)
                            return
                    elif k == 2:
                        if self.load_soundfont():
                            i = 0
                            warn = pxr.select_sfpreset(i)
                elif sb.left == SB.HOLD:
                    sb.lcd_clear()
                    pxr.load_bank()
                    self.select_patch(0)
                    return
                elif sb.right == SB.LONG:
                    self.reload_bank()
                    return
                elif sb.left == SB.LONG: self.panic_restart()
                else: continue
                break

    def effects_menu(self):
        i=0
        fxmenu_info = (
('Reverb Size', 'synth.reverb.room-size', '4.1f', 0.1, 0.0, 1.0),
('Reverb Damp', 'synth.reverb.damp', '4.1f', 0.1, 0.0, 1.0),
('Rev. Width', 'synth.reverb.width', '5.1f', 1.0, 0.0, 100.0),
('Rev. Level', 'synth.reverb.level', '5.2f', 0.01, 0.00, 1.00),
('Chorus Voices', 'synth.chorus.nr', '2d', 1, 0, 99),
('Chor. Level', 'synth.chorus.level', '4.1f', 0.1, 0.0, 10.0),
('Chor. Speed', 'synth.chorus.speed', '4.1f', 0.1, 0.1, 21.0),
('Chorus Depth', 'synth.chorus.depth', '3.1f', 0.1, 0.3, 5.0),
('Gain', 'synth.gain', '11.1f', 0.1, 0.0, 5.0))
        while True:
            fxopts = []
            args = []
            for name, opt, fmt, inc, min, max in fxmenu_info[i:] + fxmenu_info[0:i]:
                curval = pxr.fluid_get(opt)
                fxopts.append(name + ':' + format(curval, fmt))
                args.append((curval, inc, min, max, fmt, opt))
            sb.lcd_write("Effects:", 0)
            j = sb.choose_opt(fxopts, row=1)
            if j < 0: break
            sb.lcd_write(fxopts[j], 0)
            newval = sb.choose_val(*args[j][0:5])
            if sb.choose_opt(["set?" + format(newval, args[j][4]).rjust(12)], row=1) > -1:
                pxr.fluid_set(args[j][5], newval, updatebank=True, patch=self.pno)
            i = (i + j) % len(fxmenu_info)

    def system_menu(self):
        sb.lcd_write("Options:", 0)
        k = sb.choose_opt(['Power Down', 'MIDI Devices', 'Wifi Settings', 'Add From USB', 'Update Device'], row=1, passlong=True)
        if k == 0:
            sb.lcd_write("Shutting down...", 0)
            sb.lcd_write("Wait 30s, unplug", 1)
            subprocess.run('sudo shutdown -h now'.split())            
        elif k == 1: self.midi_devices()
        elif k == 2: self.wifi_settings()
        elif k == 3: self.addfrom_usb()
        elif k == 4: self.update_device()

    def midi_devices(self):
        sb.lcd_write("MIDI Devices:", 0)
        outports = pxr.list_midi_outputs()
        op = sb.choose_opt(outports + ["MIDI monitor.."], row=1, scroll=True, timeout=0)
        if op < 0: return
        if 0 < op < len(outports):
            sb.lcd_write("Connect to:", 0)
            inports = pxr.list_midi_inputs()
            ip = sb.choose_opt(inports, row=1)
            if ip < 0: return
            outport = re.search("\d+:\d+$", outports[op])[0]
            inport = re.search("\d+:\d+$", inports[ip])[0]
            subprocess.run(['aconnect', inport, outport])
        elif op == len(outports):
            self.midi_monitor()

    def midi_monitor(self):
        msg = self.latest_midimessage
        sb.lcd_clear()
        sb.lcd_write("MIDI monitor:", 0)
        while True:
            if sb.waitfortap(0.1): return
            if self.latest_midimessage == msg: continue
            msg = self.latest_midimessage
            if msg.type == 'note':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}note{msg.par1:3}={msg.par2:<3}", 1)
            if msg.type == 'noteoff':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}noff{msg.par1:3}={msg.par2:<3}", 1)
            if msg.type == 'cc':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}  cc{msg.par1:3}={msg.par2:<3}", 1)
            if msg.type == 'kpress':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}keyp{msg.par1:3}={msg.par2:<3}", 1)
            if msg.type == 'pbend':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}pbend={msg.par1:<5}", 1)
            if msg.type == 'cpress':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}atouch={msg.par1:<4}", 1)
            if msg.type == 'prog':
                sb.lcd_write(f"Ch{msg.chan + 1:<3}program={msg.par1:<3}", 1)

    def wifi_settings(self):
        # display current connection
        x = re.search("SSID: ([^\n]+)", subprocess.check_output('iw dev wlan0 link'.split()).decode())
        ssid = x[1] if x else "Not connected"
        ip = subprocess.check_output(['hostname', '-I']).decode().strip()
        sb.lcd_clear()
        sb.lcd_write(ssid, 0)
        sb.lcd_write(ip, 1, rjust=True)
        if not sb.waitfortap(10): return
        # connections menu
        while True:
            sb.lcd_write("Connections:", 0)
            if self.nwlink:
                opts = self.networks + ['Rescan...', 'Block NetLink']
            else:
                opts = self.networks + ['Rescan...', 'Allow NetLink']
            j = sb.choose_opt(opts, row=1, scroll=True, timeout=0)
            if j < 0: return
            elif j == len(opts) - 1:
                if self.nwlink:
                    self.nwlink = None
                    pxr.cfg['netlink_active'] = 0
                else:
                    port = pxr.cfg.get('netlink_port', netlink.DEFAULT_PORT)
                    passkey = pxr.cfg.get('netlink_passkey', netlink.DEFAULT_PASSKEY)
                    self.nwlink = netlink.Server(port, passkey)
                    pxr.cfg['netlink_active'] = 1
                pxr.write_config()
                return
            elif j == len(opts) - 2:
                sb.lcd_write("scanning..", 1)
                x = subprocess.check_output('sudo iw wlan0 scan'.split()).decode()
                self.networks = [s for s in re.findall('SSID: ([^\n]*)', x) if s]
            else:
                sb.lcd_write("Password:", 0)
                newpsk = sb.char_input(charset = SB.PRNCHARS)
                if newpsk == '': return
                sb.lcd_clear()
                sb.lcd_write(networks[j], 0)
                sb.lcd_write("adding network..", 1)
                e = subprocess.Popen(('echo', f'network={{\n  ssid="{networks[j]}"\n  psk="{newpsk}"\n}}\n'), stdout=subprocess.PIPE)
                subprocess.run(('sudo', 'tee', '-a', '/etc/wpa_supplicant/wpa_supplicant.conf'), stdin=e.stdout, stdout=subprocess.DEVNULL)
                subprocess.run('sudo systemctl restart dhcpcd'.split())
                self.wifi_settings()
                return

    @staticmethod
    def addfrom_usb():
        sb.lcd_clear()
        sb.lcd_write("looking for USB ", 0)
        b = subprocess.check_output(['sudo', 'blkid']).decode()
        x = re.findall('/dev/sd[a-z]\d+', b)
        if not x:
            sb.lcd_write("USB not found!", 1)
            sb.waitforrelease(2)
            return
        sb.lcd_write("copying files..", 1)
        try:
            subprocess.run(['sudo', 'mkdir', '-p', '/mnt/usbdrv'])
            for usb in x:
                subprocess.run(['sudo', 'mount', usb, '/mnt/usbdrv/'], timeout=30)
                for src in Path('/mnt/usbdrv').rglob('*'):
                    if not src.is_file(): continue
                    dest = 'SquishBox' / src.relative_to('/mnt/usbdrv')
                    if not dest.parent.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
                subprocess.run(['sudo', 'umount', usb], timeout=30)
        except Exception as e:
            sb.lcd_write("halted - errors:", 0)
            sb.lcd_write(str(e).replace('\n', ' '), 1)
            while not sb.waitfortap(10): pass
        else:
            sb.lcd_write("copying files..", 0)
            sb.lcd_write("done!", 1, rjust=True)
            sb.waitforrelease(1)

    @staticmethod
    def update_device():
        sb.lcd_write(f"Firmware {VERSION}", 0, scroll=True)
        sb.lcd_write("checking..", 1, rjust=True)
        x = subprocess.check_output(['curl', 'https://raw.githubusercontent.com/albedozero/fluidpatcher/master/patcher/__init__.py'])
        newver = re.search("VERSION = '([0-9\.]+)'", x.decode())[1]
        subprocess.run(['sudo', 'apt-get', 'update'])
        u = subprocess.check_output(['sudo', 'apt-get', 'upgrade', '-sy'])
        fup, sysup = 0, 0
        if [int(x) for x in newver.split('.')] > [int(x) for x in VERSION.split('.')]:
            fup = True if sb.choose_opt([f"install {newver}?"], row=1, timeout=0) == 0 else False
        else:
            sb.lcd_write("Up to date!", 1, rjust=True)
            sb.waitfortap(10)
        if not re.search('0 upgraded, 0 newly installed', u.decode()):
            sb.lcd_write("OS out of date", 0)
            sysup = True if sb.choose_opt(['upgrade?'], row=1, timeout=0) == 0 else False
        if not (fup or sysup):
            return
        sb.lcd_write("updating..", 0)
        sb.lcd_write("please wait", 1, rjust=True)
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
            subprocess.run(['sudo', 'reboot'])
        except Exception as e:
            sb.lcd_write("halted - errors:", 1, scroll=True)
            sb.lcd_write(str(e).replace('\n', ' '), 1)
            while not sb.waitfortap(10): pass

    @staticmethod
    def panic_restart():
        sb.lcd_clear()
        sb.lcd_blink("Panic Restart", 0)
        sb.waitforrelease(1)
        sys.exit(1)

    def netlink_poll(self):
        if not self.nwlink: return
        if not self.nwlink.pending(): return
        req = self.nwlink.requests.pop(0)
        if req.type == netlink.SEND_VERSION:
            self.nwlink.reply(req, VERSION)
        elif req.type == netlink.RECV_BANK:
            if self.load_bank(req.body):
                self.nwlink.reply(req, pxr.render_fpyaml(pxr.patches))
                self.select_patch(0)
            else:
                self.nwlink.reply(req, "Error in bank file", netlink.REQ_ERROR)
        elif req.type == netlink.LIST_BANKS:
            self.nwlink.reply(req, pxr.render_fpyaml(pxr.banks))
        elif req.type == netlink.LOAD_BANK:
            bank = req.body if req.body else pxr.currentbank
            rawbank = self.load_bank(bank)
            if rawbank:
                self.nwlink.reply(req, pxr.render_fpyaml(bank, rawbank, pxr.patches))
                self.select_patch(0)
            else:
                self.nwlink.reply(req, "Unable to load bank file", netlink.REQ_ERROR)
        elif req.type == netlink.SAVE_BANK:
            bfile, rawbank = pxr.parse_fpyaml(req.body)
            if self.load_bank(rawbank):
                self.save_bank(bfile)
                self.nwlink.reply(req)
            else:
                self.nwlink.reply(req, "Unable to save bank file", netlink.REQ_ERROR)
        elif req.type == netlink.SELECT_PATCH:
            if req.body in pxr.patches:
                self.nwlink.reply(req)
                self.select_patch(pxr.patches.index(req.body))
            else:
                self.nwlink.reply(req, "Patch not found", netlink.REQ_ERROR)
        elif req.type == netlink.LIST_SOUNDFONTS:
            self.nwlink.reply(req, pxr.render_fpyaml(pxr.soundfonts))
        elif req.type == netlink.LOAD_SOUNDFONT:
            if self.load_soundfont(req.body):
                self.nwlink.reply(req, pxr.render_fpyaml(pxr.sfpresets))
                self.presetmode()
            else:
                self.nwlink.reply(req, f"Unable to load {req.body}", netlink.REQ_ERROR)
        elif req.type == netlink.SELECT_SFPRESET:
            if int(req.body) < len(pxr.sfpresets):
                self.nwlink.reply(req)
                self.presetmode(int(req.body))
            else:
                self.nwlink.reply(req, "Preset not found", netlink.REQ_ERROR)
        elif req.type == netlink.LIST_PLUGINS:
            try: info = subprocess.check_output(['listplugins']).decode()
            except: self.nwlink.reply(req, 'No plugins installed')
            else: self.nwlink.reply(req, pxr.render_fpyaml(info))
        elif req.type == netlink.LIST_PORTS:
            self.nwlink.reply(req, pxr.render_fpyaml(pxr.list_midi_inputs()))
        elif req.type == netlink.READ_CFG:
            self.nwlink.reply(req, pxr.render_fpyaml(pxr.cfgfile, pxr.read_config()))
        elif req.type == netlink.SAVE_CFG:
            try: pxr.write_config(req.body)
            except PatcherError as e: self.nwlink.reply(req, str(e), netlink.REQ_ERROR)
            else: self.nwlink.reply(req)


os.umask(0o002)

sb = SB.StompBox()
sb.lcd_clear()
sb.lcd_write(f"SquishBox {VERSION}", 0)

cfgfile = sys.argv[1] if len(sys.argv) > 1 else '/home/pi/SquishBox/squishboxconf.yaml'
try: pxr = Patcher(cfgfile)
except PatcherError:
    sb.lcd_write("bad config file!", 1)
    sys.exit("bad config file")
    
mainapp = SquishBox()
