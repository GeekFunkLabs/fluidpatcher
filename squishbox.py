#!/usr/bin/env python3
"""
Description: an implementation of patcher.py for a Raspberry Pi in a stompbox
"""
import re, sys, os, subprocess, shutil, tempfile
from pathlib import Path
from patcher import Patcher, PatcherError, VERSION
from utils import netlink, stompboxpi as SB

def load_bank_menu():
    if not pxr.banks:
        sb.lcd_write("no banks found!", 1)
        sb.waitforrelease(2)
        return False
    sb.lcd_write("Load Bank:", 0)
    i = sb.choose_opt([str(b) for b in pxr.banks], row=1, scroll=True, timeout=0)
    if i < 0: return False
    sb.lcd_write(" loading patches", 1)
    try:
        pxr.load_bank(pxr.banks[i])
    except PatcherError:
        sb.lcd_write("bank load error!", 1)
        sb.waitforrelease(2)
        return False
    pxr.write_config()
    sb.waitforrelease(1)
    return True

def midimessage_listener(msg):
    global last_midimessage
    if hasattr(msg, 'val'):
        pass # handle triggers for midi/mp3 player/looper, etc.
    else:
        last_midimessage = msg

os.umask(0o002)

sb = SB.StompBox()
sb.lcd_clear()
sb.lcd_write(f"SquishBox {VERSION}", 0)

# start the patcher
if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
else:
    cfgfile = '/home/pi/SquishBox/squishboxconf.yaml'
try:
    pxr = Patcher(cfgfile)
except PatcherError:
    sb.lcd_write("bad config file!", 1)
    sys.exit("bad config file")

# initialize network link
if pxr.cfg.get('remotelink_active', 0):
    port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
    passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
    remote_link = netlink.Server(port, passkey)
else:
    remote_link = None

# load bank
sb.lcd_write("loading patches", 1, rjust=True)
try:
    pxr.load_bank(pxr.currentbank)
except PatcherError:
    while True:
        sb.lcd_write("bank load error!", 1)
        sb.waitfortap(10)
        if load_bank_menu():
            break

networks = []
fxmenu_info = (
('Reverb Size', 'synth.reverb.room-size', '4.1f', 0.1, 0.0, 1.0),
('Reverb Damp', 'synth.reverb.damp', '4.1f', 0.1, 0.0, 1.0),
('Rev. Width', 'synth.reverb.width', '5.1f', 1.0, 0.0, 100.0),
('Rev. Level', 'synth.reverb.level', '5.2f', 0.01, 0.00, 1.00),
('Chorus Voices', 'synth.chorus.nr', '2d', 1, 0, 99),
('Chor. Level', 'synth.chorus.level', '4.1f', 0.1, 0.0, 10.0),
('Chor. Speed', 'synth.chorus.speed', '4.1f', 0.1, 0.1, 21.0),
('Chorus Depth', 'synth.chorus.depth', '3.1f', 0.1, 0.3, 5.0),
('Gain', 'synth.gain', '11.1f', 0.1, 0.0, 5.0)
)
last_midimessage = None
pxr.set_midimessage_callback(midimessage_listener)
pno = 0
warn = pxr.select_patch(pno)

# update LCD
while True:
    sb.lcd_clear()
    if pxr.sfpresets:
        ptot = len(pxr.sfpresets)
        p = pxr.sfpresets[pno]
        sb.lcd_write(p.name, 0, scroll=True)
        sb.lcd_write(f"preset {p.bank:03}:{p.prog:03}", 1, rjust=True)
    else:
        ptot = pxr.patches_count()
        patchname = pxr.patch_name(pno)
        sb.lcd_write(patchname, 0, scroll=True)
        sb.lcd_write(f"patch: {pno + 1}/{ptot}", 1, rjust=True)
    if warn:
        sb.lcd_write(';'.join(warn), 1, scroll=True)

    # input loop
    while True:
        sb.update()

        # patch/preset switching
        if SB.TAP in sb.buttons:
            if warn:
                warn = []
                break
            if sb.right == SB.TAP:
                pno = (pno + 1) % ptot
            elif sb.left == SB.TAP:
                pno = (pno - 1) % ptot
            if pxr.sfpresets:
                warn = pxr.select_sfpreset(pno)
            else:
                warn = pxr.select_patch(pno)
            break

        # right button menu
        if sb.right == SB.HOLD:
            k = sb.choose_opt(['Save Patch', 'Delete Patch', 'Load Bank', 'Save Bank', 'Load Soundfont', 'Effects..'], row=1, passlong=True)
            
            if k == 0: # save the current patch or save preset to a patch
                sb.lcd_write("Save patch:", 0)
                if pxr.sfpresets:
                    newname = sb.char_input(pxr.sfpresets[pno].name)
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
                warn = pxr.select_patch(pno)
                
            elif k == 1: # delete patch if it's not last one or a preset; ask confirm
                if pxr.sfpresets or ptot < 2:
                    sb.lcd_write("cannot delete", 1)
                    sb.waitforrelease(2)
                    break
                j = sb.choose_opt(['confirm delete?', 'cancel'], row=1)
                if j == 0:
                    pxr.delete_patch(patchname)
                    pno = min(pno, (ptot - 2))
                    warn = pxr.select_patch(pno)
                    
            elif k == 2: # load bank
                if not load_bank_menu(): break
                pno = 0
                warn = pxr.select_patch(pno)
                pxr.write_config()
                
            elif k == 3: # save bank, prompt for name
                if pxr.sfpresets:
                    sb.lcd_write("cannot save", 1)
                    sb.waitforrelease(2)
                    break
                sb.lcd_write("Save bank:", 0)
                bankfile = sb.char_input(pxr.currentbank)
                if bankfile == '': break
                try:
                    pxr.save_bank(bankfile)
                except PatcherError:
                    sb.lcd_write("bank save error!", 1)
                    sb.waitforrelease(2)
                    break
                pxr.write_config()
                sb.lcd_write("bank saved.", 1)
                sb.waitforrelease(1)
                
            elif k == 4: # load soundfont
                if not pxr.soundfonts:
                    sb.lcd_write("no soundfonts!", 1)
                    sb.waitforrelease(2)
                    break
                sb.lcd_write("Load Soundfont:", 0)
                s = sb.choose_opt([str(sf) for sf in pxr.soundfonts], row=1, scroll=True, timeout=0)
                if s < 0: break
                sb.lcd_write("loading...", 1)
                if not pxr.load_soundfont(pxr.soundfonts[s]):
                    sb.lcd_write("unable to load!", 1)
                sb.waitforrelease(2)
                pno = 0
                warn = pxr.select_sfpreset(pno)
                
            elif k == 5: # effects menu
                i=0
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
                        pxr.fluid_set(args[j][5], newval, updatebank=True, patch=pno)
                    i = (i + j) % len(fxmenu_info)
            break

            
        # left button menu - system-related tasks
        if sb.left == SB.HOLD:
            sb.lcd_write("Options:", 0)
            k = sb.choose_opt(['Power Down', 'MIDI Devices', 'Wifi Settings', 'Add From USB', 'Update Device'], row=1, passlong=True)
            
            if k == 0: # power down
                sb.lcd_write("Shutting down...", 0)
                sb.lcd_write("Wait 30s, unplug", 1)
                subprocess.run('sudo shutdown -h now'.split())
                
            elif k == 1: # midi device list/monitor
                sb.lcd_write("MIDI Devices:", 0)
                outports = pxr.list_midi_outputs()
                op = sb.choose_opt(outports + ["MIDI monitor.."], row=1, scroll=True, timeout=0)
                if op < 0: break
                if op < len(outports):
                    sb.lcd_write("Connect to:", 0)
                    inports = pxr.list_midi_inputs()
                    ip = sb.choose_opt(inports, row=1)
                    if ip < 0: break
                    outport = re.search("\d+:\d+$", outports[op])[0]
                    inport = re.search("\d+:\d+$", inports[ip])[0]
                    subprocess.run(['aconnect', inport, outport])
                else:
                    msg = last_midimessage
                    sb.lcd_clear()
                    sb.lcd_write("MIDI monitor:", 0)
                    while True:
                        if sb.waitfortap(0.1): break
                        if last_midimessage == msg: continue
                        msg = last_midimessage
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

            elif k == 2: # wifi settings
                while True:
                    x = re.search("SSID: ([^\n]+)", subprocess.check_output('iw dev wlan0 link'.split()).decode())
                    ssid = x[1] if x else "Not connected"
                    ip = subprocess.check_output(['hostname', '-I']).decode().strip()
                    sb.lcd_clear()
                    sb.lcd_write(ssid, 0)
                    sb.lcd_write(ip, 1, rjust=True)
                    if not sb.waitfortap(10):
                        j = -2
                        break
                    sb.lcd_write("Connections:", 0)
                    while True:
                        if remote_link:
                            opts = networks + ['Rescan...', 'Block RemoteLink']
                        else:
                            opts = networks + ['Rescan...', 'Allow RemoteLink']
                        j = sb.choose_opt(opts, row=1, scroll=True, timeout=0)
                        if j < 0: break
                        if j == len(opts) - 1:
                            if remote_link:
                                remote_link = None
                                pxr.cfg['remotelink_active'] = 0
                            else:
                                port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
                                passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
                                remote_link = netlink.Server(port, passkey)
                                pxr.cfg['remotelink_active'] = 1
                            pxr.write_config()
                            break
                        if j == len(opts) - 2:
                            sb.lcd_write("scanning..", 1)
                            x = subprocess.check_output('sudo iw wlan0 scan'.split()).decode()
                            networks = [s for s in re.findall('SSID: ([^\n]*)', x) if s]
                        else:
                            sb.lcd_write("Password:", 0)
                            newpsk = sb.char_input(charset = SB.PRNCHARS)
                            if newpsk == '': break
                            sb.lcd_clear()
                            sb.lcd_write(networks[j], 0)
                            sb.lcd_write("adding network..", 1)
                            e = subprocess.Popen(('echo', f'network={{\n  ssid="{networks[j]}"\n  psk="{newpsk}"\n}}\n'), stdout=subprocess.PIPE)
                            subprocess.run(('sudo', 'tee', '-a', '/etc/wpa_supplicant/wpa_supplicant.conf'), stdin=e.stdout, stdout=subprocess.DEVNULL)
                            subprocess.run('sudo systemctl restart dhcpcd'.split())
                            j = -2
                            break
                    if j > -2: break

            elif k == 3: # copy files from a flash drive into SquishBox directory
                sb.lcd_clear()
                sb.lcd_write("looking for USB ", 0)
                b = subprocess.check_output(['sudo', 'blkid']).decode()
                x = re.findall('/dev/sd[a-z]\d+', b)
                if not x:
                    sb.lcd_write("USB not found!", 1)
                    sb.waitforrelease(2)
                    break
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

            elif k == 4: # update firmware and/or system
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
                    break
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

            break


        # long-hold right button = reload bank
        if sb.right == SB.LONG:
            sb.lcd_clear()
            sb.lcd_blink("Reloading Bank", 0)
            lastpatch = pxr.patch_name(pno)
            pxr.load_bank(pxr.currentbank)
            try:
                pno = pxr.patch_index(lastpatch)
            except PatcherError:
                if pno >= pxr.patches_count():
                    pno = 0
            warn = pxr.select_patch(pno)
            sb.waitforrelease(1)
            break


        # long-hold left button = panic
        if sb.left == SB.LONG:
            sb.lcd_clear()
            sb.lcd_blink("Panic Restart", 0)
            sb.waitforrelease(1)
            sys.exit(1)


        # check remote link for requests
        if remote_link and remote_link.pending():
            req = remote_link.requests.pop(0)
            
            if req.type == netlink.SEND_VERSION:
                remote_link.reply(req, VERSION)
            
            elif req.type == netlink.RECV_BANK:
                try:
                    pxr.load_bank(req.body)
                except PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, pxr.render_fpyaml(pxr.patch_names()))
                    
            elif req.type == netlink.LIST_BANKS:
                if not pxr.banks:
                    remote_link.reply(req, "no banks found!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, pxr.render_fpyaml(pxr.banks))
                
            elif req.type == netlink.LOAD_BANK:
                sb.lcd_write(req.body, 0)
                sb.lcd_write(" loading patches", 1)
                try:
                    if req.body == '':
                        rawbank = pxr.load_bank()
                    else:
                        rawbank = pxr.load_bank(req.body)
                except PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                    sb.lcd_write("bank load error!", 1)
                    sb.waitforrelease(2)
                else:
                    info = pxr.render_fpyaml(pxr.currentbank, rawbank, pxr.patch_names())
                    remote_link.reply(req, info)
                    pxr.write_config()
                    
            elif req.type == netlink.SAVE_BANK:
                bfile, rawbank = pxr.parse_fpyaml(req.body)
                try:
                    pxr.save_bank(bfile, rawbank)
                except PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req)
                    pxr.write_config()
                            
            elif req.type == netlink.SELECT_PATCH:
                try:
                    if req.body.isdecimal():
                        pno = int(req.body)
                    else:
                        pno = pxr.patch_index(req.body)
                    warn = pxr.select_patch(pno)
                except PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, warn)
                    break
                    
            elif req.type == netlink.LIST_SOUNDFONTS:
                if not pxr.soundfonts:
                    remote_link.reply(req, "No soundfonts!", netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, pxr.render_fpyaml(pxr.soundfonts))
            
            elif req.type == netlink.LOAD_SOUNDFONT:
                sb.lcd_write(req.body, 0)
                sb.lcd_write("loading...", 1)
                if not pxr.load_soundfont(req.body):
                    sb.lcd_write("unable to load!", 1)
                    remote_link.reply(req, "Unable to load " + req.body, netlink.REQ_ERROR)
                else:
                    remote_link.reply(req, pxr.render_fpyaml(pxr.sfpresets))
            
            elif req.type == netlink.SELECT_SFPRESET:
                pno = int(req.body)
                warn = pxr.select_sfpreset(pno)
                remote_link.reply(req, warn)
                break

            elif req.type == netlink.LIST_PLUGINS:
                try:
                    info = subprocess.check_output(['listplugins']).decode()
                except:
                    remote_link.reply(req, 'No plugins installed')
                else:
                    remote_link.reply(req, pxr.render_fpyaml(info))

            elif req.type == netlink.LIST_PORTS:
                ports = pxr.list_midi_inputs()
                remote_link.reply(req, pxr.render_fpyaml(ports))

            elif req.type == netlink.READ_CFG:
                info = pxr.render_fpyaml(pxr.cfgfile, pxr.read_config())
                remote_link.reply(req, info)

            elif req.type == netlink.SAVE_CFG:
                try:
                    pxr.write_config(req.body)
                except PatcherError as e:
                    remote_link.reply(req, str(e), netlink.REQ_ERROR)
                else:
                    remote_link.reply(req)
