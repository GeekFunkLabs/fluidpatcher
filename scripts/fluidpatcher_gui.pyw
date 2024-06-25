#!/usr/bin/env pythonw
"""
Description: a graphical implementation of fluidpatcher
             for composing/editing bank files or live playing
"""

from pathlib import Path
import sys
import tkinter as tk
from tkinter.font import Font
import tkinter.ttk as ttk
import tkinter.messagebox as msgbox
import tkinter.filedialog as filedlg
import traceback
import webbrowser

from fluidpatcher import FluidPatcher, __version__

WIDTH = 500
HEIGHT = 300
XPOS = 50
YPOS = 50
FONTSIZE = 24
PAD = 10
FILLSCREEN = False

MSG_TYPES = 'note', 'noteoff', 'kpress', 'cc', 'prog', 'pbend', 'cpress'
MSG_NAMES = "Note On", "Note Off", "Key Pressure", "Control Change", "Program Change", "Pitch Bend", "Aftertouch"

def gui_excepthook(etype, val, tb):
    s = traceback.format_exception(etype, val, tb)
    msgbox.showerror("Error", ''.join(s))


class PersistentDialog(tk.Toplevel):

    def __init__(self, master, hint=""):
        super().__init__()
        self.master = master
        self.protocol('WM_DELETE_WINDOW', self.hide)
        self.last_geometry = hint

    def show(self, *_):
        if self.state() == 'normal':
            self.last_geometry = self.geometry()
            self.withdraw()
        else:
            self.transient(self.master)
            self.geometry(self.last_geometry)
            self.deiconify()
            
    def hide(self, *_):
        self.last_geometry = self.geometry()
        self.withdraw()

   
class PresetChooser(PersistentDialog):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.plist = ttk.Treeview(self, columns=('bank', 'prog', 'name'), show='headings', selectmode='browse')
        ysc = ttk.Scrollbar(self, orient='vertical', command=self.plist.yview)
        self.plist.configure(yscrollcommand=ysc.set)
        self.plist.heading(0, text='Bank')
        self.plist.heading(1, text='Program')
        self.plist.heading(2, text='Name')
        self.plist.column(0, width=75)
        self.plist.column(1, width=75)
        self.plist.column(2, width=200)
        ysc.pack(side='right', fill='y')
        self.plist.pack(fill='both', expand=True)
        self.plist.bind('<<TreeviewSelect>>', self.preset_select)
        self.plist.bind('<Double-Button-1>', self.ok)
        self.bind('<KeyPress-Return>', self.ok)
        self.bind('<KeyPress-Escape>', self.cancel)
        self.protocol('WM_DELETE_WINDOW', self.cancel)

    def preset_select(self, *_):
        if (self.plist.selection()) == ():
            self.preset_text = ""
        else:
            bank, prog, name = self.presets[int(self.plist.selection()[0])]
            warn = self.master.fp.select_sfpreset(self.title(), bank, prog)
            if warn:
                msgbox.showwarning("Preset Warning", '\n'.join(warn))
            self.preset_text = f"{self.title()}:{bank:03d}:{prog:03d}"

    def getpreset(self, sfrel, presets):
        self.title(sfrel)
        self.presets = presets
        for i in self.plist.get_children():
            self.plist.delete(i)
        for i, (bank, prog, name) in enumerate(presets):
            self.plist.insert('', 'end', iid=str(i), values=(f"{bank:03d}", f"{prog:03d}", name))
        self.plist.selection_set("0")
        self.show()
        self.wait_visibility()
        self.grab_set()

    def ok(self, *_):
        self.grab_release()
        self.hide()
        self.master.bedit.text.insert('insert', self.preset_text)
        self.master.bedit.text.see('insert')
        self.master.bedit.text.focus_set()
        self.master.parse_bank()
    
    def cancel(self, *_):
        self.grab_release()
        self.hide()


class SettingsDialog(PersistentDialog):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title(cfgfile)
        self.cfg = tk.Text(self, wrap='none')
        xsc = ttk.Scrollbar(self, orient='horizontal', command=self.cfg.xview)
        ysc = ttk.Scrollbar(self, orient='vertical', command=self.cfg.yview)
        bf = ttk.Frame(self, relief='groove', padding=10)
        self.cfg.configure(xscrollcommand=xsc.set, yscrollcommand=ysc.set)
        self.cfg.grid(row=0, column=0, sticky='nsew')
        ysc.grid(row=0, column=1, sticky='ns')
        xsc.grid(row=1, column=0, sticky='ew')
        bf.grid(row=2, column=0, sticky='ew', columnspan=2)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        applybtn = ttk.Button(bf, text="Apply", command=self.apply)
        cancelbtn = ttk.Button(bf, text="Cancel", command=self.cancel)
        cancelbtn.pack(side='right')
        applybtn.pack(side='right')
        self.protocol('WM_DELETE_WINDOW', self.cancel)

    def viewsettings(self):
        self.cfg.delete('1.0', 'end')
        self.cfg.insert('1.0', cfgfile.read_text())
        self.show()
        self.wait_visibility()
        self.grab_set()

    def apply(self):
        cfgfile.write_text(self.cfg.get('1.0', 'end'))
        try:
            self.master.fp = FluidPatcher(cfgfile)
        except Exception as e:
            msgbox.showerror("Configuration Error", f"Error in config file {cfgfile}:\n{str(e)}")
        else:
            self.grab_release()
            self.hide()
            self.master.fp.midi_callback = self.master.listener
            self.master.parse_bank()
            
    def cancel(self):
        self.grab_release()
        self.hide()


class MainWindow(ttk.Frame):

    def __init__(self):
        try:
            self.fp = FluidPatcher(cfgfile)
        except Exception as e:
            msgbox.showerror("Configuration Error", f"Error in config file {cfgfile}:\n{str(e)}")
            sys.exit() # open settings dialog instead!
    
        super().__init__()
        self.master.title('FluidPatcher')
        self.master.geometry(f'{WIDTH}x{HEIGHT}+{XPOS}+{YPOS}')
        self.master.protocol('WM_DELETE_WINDOW', self.menu_exit)

        # create the bank editor window
        self.bedit = PersistentDialog(self, f'+{XPOS + WIDTH + 20}+{YPOS}')
        self.bedit.text = tk.Text(self.bedit, wrap='none', undo=True)
        xsc = ttk.Scrollbar(self.bedit, orient='horizontal', command=self.bedit.text.xview)
        ysc = ttk.Scrollbar(self.bedit, orient='vertical', command=self.bedit.text.yview)
        self.bedit.text.configure(xscrollcommand=xsc.set, yscrollcommand=ysc.set)
        self.bedit.text.grid(row=0, column=0, sticky='nsew')
        ysc.grid(row=0, column=1, sticky='ns')
        xsc.grid(row=1, column=0, sticky='ew')
        self.bedit.grid_columnconfigure(0, weight=1)
        self.bedit.grid_rowconfigure(0, weight=1)
        self.bedit.withdraw()
        self.bedit.text.bind('<KeyRelease>', self.parse_bank)

        # create the midi monitor window
        self.midimon = PersistentDialog(self, f'+{XPOS}+{YPOS + HEIGHT + 75}')
        self.midimon.title("MIDI Monitor")
        self.midimon.msglist = ttk.Treeview(self.midimon, columns=('type', 'chan', 'data'), show='headings', selectmode='none')
        ysc = ttk.Scrollbar(self.midimon, orient='vertical', command=self.midimon.msglist.yview)
        self.midimon.msglist.configure(yscrollcommand=ysc.set)
        self.midimon.msglist.heading(0, text='Type')
        self.midimon.msglist.heading(1, text='Channel')
        self.midimon.msglist.heading(2, text='Data')
        self.midimon.msglist.column(0, width=120)
        self.midimon.msglist.column(1, width=60)
        self.midimon.msglist.column(2, width=100)
        ysc.pack(side='right', fill='y')
        self.midimon.msglist.pack(fill='both', expand=True)
        self.midimon.withdraw()

        # create the preset chooser window
        self.presetdlg = PresetChooser(self)
        self.presetdlg.withdraw()

        # create the settings dialog
        self.settingsdlg = SettingsDialog(self)
        self.settingsdlg.withdraw()

        # create the main menu
        self.menu = tk.Menu(self)
        fm = tk.Menu(self.menu, tearoff=0)
        fm.add_command(label='New Bank', underline=0, command=self.menu_new, accelerator='Ctrl+N')
        fm.add_command(label='Load Bank', underline=1, command=self.menu_open, accelerator='Ctrl+O')
        fm.add_command(label='Save Bank', underline=0, command=self.menu_save, accelerator='Ctrl+S')
        fm.add_command(label='Save Bank As...', underline=10, command=self.menu_saveas, accelerator='Ctrl+Shift+S')
        fm.add_separator()
        fm.add_command(label='Exit', underline=1, command=self.menu_exit, accelerator='Ctrl+Q')
        self.bind_all('<Control-n>', self.menu_new)
        self.bind_all('<Control-o>', self.menu_open)
        self.bind_all('<Control-s>', self.menu_save)
        self.bind_all('<Control-S>', self.menu_saveas)
        self.bind_all('<Control-q>', self.menu_exit)
        
        self.patchmenu = tk.Menu(self.menu, tearoff=0)
        
        tm = tk.Menu(self.menu, tearoff=0)
        tm.add_command(label="Edit Bank", underline=5, command=self.bedit.show, accelerator='Ctrl+B')
        tm.add_command(label="Choose Preset", underline=7, command=self.menu_choosepreset, accelerator='Ctrl+P')
        tm.add_command(label="Midi Monitor", underline=0, command=self.menu_midimon, accelerator='Ctrl+M')
        tm.add_command(label="Fill Screen", underline=0, command=self.menu_fillscreen, accelerator='F11')
        tm.add_separator()
        tm.add_command(label="Settings", underline=0, command=self.settingsdlg.viewsettings)
        self.bind_all('<Control-b>', self.bedit.show)
        self.bind_all('<Control-p>', self.menu_choosepreset)
        self.bind_all('<Control-m>', self.menu_midimon)
        self.bind_all('<F11>', self.menu_fillscreen)
        for key in 'bnop':
            self.bind_class('Text', f'<Control-{key}>', lambda _: ())
        
        hm = tk.Menu(self.menu, tearoff=0, name='help')
        hm.add_command(label='Quick Help', underline=6,
                             command=lambda: webbrowser.open('https://geekfunklabs.github.io/fluidpatcher/basic_usage/#fluidpatcher_guipyw'))
        hm.add_command(label='Documentation', underline=0,
                             command=lambda: webbrowser.open('https://geekfunklabs.github.io/fluidpatcher'))
        hm.add_command(label='About', underline=0, command=lambda: msgbox.showinfo("About", f"""
FluidPatcher {__version__}
github.com/albedozero/fluidpatcher

by Bill Peterson
geekfunklabs.com

Python version {sys.version.split()[0]}
"""))

        self.menu.add_cascade(label='File', underline=0, menu=fm)
        self.menu.add_cascade(label='Patches', underline=0, menu=self.patchmenu)
        self.menu.add_cascade(label='Tools', underline=0, menu=tm)
        self.menu.add_cascade(label='Help', underline=0, menu=hm)
        self.master.configure(menu=self.menu)

        # create the UI
        self.ui = tk.Canvas(self)
        w, h = WIDTH, HEIGHT
        fh = int(FONTSIZE * 1.6)
        font1 = Font(size=FONTSIZE)
        font2 = Font(size=int(0.8 * FONTSIZE))
        h2 = fh * 3 + PAD * 4
        self.ui.create_rectangle(0, 0, 0, 0, fill='#0064ff', width=0, tags='lcd')
        self.ui.create_text(0, 0, fill="white", anchor='nw', font=font1, tags='row1')
        self.ui.create_text(0, 0, fill="white", anchor='nw', font=font1, tags='row2')
        self.ui.create_text(0, 0, fill="white", anchor='ne', font=font1, tags='row3')
        self.ui.create_rectangle(0, 0, 0, 0, width=4, tags='frame')
        for i, symbol, color in ((0, '-', '#ffff00'), (1, '+', '#00ff00'), (2, '>', '#ff6464')):
            self.ui.create_rectangle(0, 0, 0, 0, fill=color, width=0, tags=f"button{i}")
            self.ui.create_text(0, 0, text=symbol, fill="black", font=font2, tags=(f"button{i}", f"symbol{i}"))
            if h > (fh + PAD) * 5 and w > (fh + PAD) * 4:
                self.ui.create_text(0, 0, fill="black", anchor='nw', font=font2, tags=(f"button{i}", f"name{i}"))
                self.ui.create_text(0, 0, fill="black", anchor='se', font=font2, tags=(f"button{i}", f"accel{i}"))
        self.ui.bind('<Configure>', self.resizeui)
        self.ui.pack(fill='both', expand=1)
        self.pack(fill='both', expand=1)
        self.pack_propagate(0)
        self.ui.tag_bind("button0", '<Button-1>', lambda _: self.select_patch((self.pno - 1) % len(self.fp.patches)))
        self.ui.tag_bind("button1", '<Button-1>', lambda _: self.select_patch((self.pno + 1) % len(self.fp.patches)))
        self.ui.tag_bind("button2", '<Button-1>', self.next_bank)
        self.bind_all('<F3>', lambda _: self.select_patch((self.pno - 1) % len(self.fp.patches)))
        self.bind_all('<F4>', lambda _: self.select_patch((self.pno + 1) % len(self.fp.patches)))
        self.bind_all('<F6>', self.next_bank)

        # initialize stuff
        self._lastfile = ''
        self.last_bankdir = self.fp.bankdir
        self.last_sfdir = self.fp.sfdir
        self.last_sfont = ""
        self.fp.midi_callback = self.listener
        self.load_bank(self.fp.currentbank)
        if FILLSCREEN: self.menu_fillscreen()

    @property        
    def lastfile(self):
        return self._lastfile

    @lastfile.setter
    def lastfile(self, bfile):
        self._lastfile = bfile
        if bfile == '':
            self.set_text(row1="(Untitled)")
            self.bedit.title("(Untitled)")
        else:
            self.set_text(row1=self._lastfile)
            self.bedit.title(self._lastfile)

    def select_patch(self, i):
        if self.lastfile == '':
            self.set_text(row1="Untitled")
        else:
            self.set_text(row1=self.lastfile)
        if self.fp.patches == []:
            self.pno = -1
            self.set_text(row2="No Patches", row3="patch 0/0")
        else:
            self.pno = i
            self.set_text(row2=self.fp.patches[self.pno],
                          row3=f"patch {self.pno + 1}/{len(self.fp.patches)}")
        warn = self.fp.apply_patch(self.pno)
        if warn:
            msgbox.showwarning("Patch Warning", '\n'.join(warn))

    def resizeui(self, event):
        w, h = event.width, event.height
        fh = int(FONTSIZE * 1.6)
        h2 = fh * 3 + PAD * 4
        self.ui.coords('lcd', 0, 0, w, h2)
        self.ui.coords('row1', PAD, PAD)
        self.ui.coords('row2', PAD, fh * 1 + PAD * 2)
        self.ui.coords('row3', w - PAD, fh * 2 + PAD * 3)
        self.ui.coords('frame', 3, 3, w - 2, h2 - 2)
        for i, name, accel in ((0, 'Prev', '[F3]'), (1, 'Next', '[F4]'), (2, 'Bank', '[F6]')):
            self.ui.coords(f"button{i}", int(w / 3 * i), h2, int(w / 3 * (i + 1)), h)
            self.ui.coords(f"symbol{i}", int(w / 3 * (i + 0.5)), int((h + h2) / 2))
            if h > (fh + PAD) * 6 and w > (fh + PAD) * 5:
                self.ui.coords(f"name{i}", int(w / 3 * i + PAD), h2 + PAD)
                self.ui.itemconfigure(f"name{i}", text=name)
                self.ui.coords(f"accel{i}", int(w / 3 * (i + 1) - PAD), h - PAD)
                self.ui.itemconfigure(f"accel{i}", text=accel)
            else:
                self.ui.itemconfigure(f"name{i}", text='')
                self.ui.itemconfigure(f"accel{i}", text='')

    def set_text(self, row1=None, row2=None, row3=None):
        if row1 != None:
            self.ui.itemconfigure('row1', text=row1)
        if row2 != None:
            self.ui.itemconfigure('row2', text=row2)
        if row3 != None:
            self.ui.itemconfigure('row3', text=row3)

    def listener(self, sig):
        if hasattr(sig, 'val'):
            if hasattr(sig, 'patch') and self.fp.patches:
                if sig.patch == -1:
                    self.select_patch((self.pno + sig.val) % len(self.fp.patches))
                else:
                    self.select_patch(sig.patch)
            elif hasattr(sig, 'lcdwrite'):
                if hasattr(sig, 'format'):
                    val = format(sig.val, sig.format)
                    self.set_text(row3=f"{sig.lcdwrite} {val}")
                else:
                    self.set_text(row3=sig.lcdwrite)
        elif sig.type in MSG_TYPES and self.midimon.state() == 'normal':
            t = MSG_TYPES.index(sig.type)
            if t < 3:
                octave = int(sig.par1 / 12) - 1
                note = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')[sig.par1 % 12]
                msg = MSG_NAMES[t], sig.chan, f"{sig.par1} ({note}{octave})={sig.par2}"
            elif t < 4:
                msg = MSG_NAMES[t], sig.chan, f"{sig.par1}={sig.par2}"
            elif t < 7:
                msg = MSG_NAMES[t], sig.chan, sig.par1
            self.midimon.msglist.insert('', 'end', values=msg)
            self.midimon.msglist.yview_moveto(1.0)

    def menu_new(self, *_):
        if self.bedit.text.edit_modified():
            resp = msgbox.askyesnocancel("New", "Unsaved changes in bank - save?")
            if resp == True: self.menu_saveas()
            elif resp == None: return
        self.lastfile = ''
        self.select_patch(0)
        self.bedit.text.delete('1.0', 'end')
        self.fp.load_bank(raw="{}")
        self.bedit.text.edit_modified(False)

    def menu_open(self, *_):
        if self.bedit.text.edit_modified():
            resp = msgbox.askyesnocancel("Load Bank", "Unsaved changes in bank - save?")
            if resp == True: self.menu_saveas()
            elif resp == None: return
        bank = filedlg.askopenfilename(initialdir=self.last_bankdir, initialfile=self.lastfile,
                                       defaultextension='.yaml',
                                       filetypes=[('Bank Files', '*.yaml')])
        if bank == '': return
        self.last_bankdir = Path(bank).parent
        self.load_bank(bank)
        
    def menu_save(self, bank=''):
        if bank == '': bank = self.lastfile
        bank = Path(bank).resolve().relative_to(self.fp.bankdir)
        try:
            self.fp.save_bank(bank, self.bedit.text.get('1.0', 'end'))
        except Exception as e:
            msgbox.showerror("Save Bank", f"Error saving {bfile}:\n{str(e)}")
            return
        self.fp.update_config()
        self.lastfile = bank
        self.bedit.text.edit_modified(False)
        
    def menu_saveas(self, *_):
        if self.bedit.text['foreground'] == 'red':
            resp = msgbox.askokcancel("Save", "Errors in bank - save anyway?")
            if resp == False: return
        bank = filedlg.asksaveasfilename(initialdir=str(self.last_bankdir), defaultextension='.yaml',
                                       filetypes=[('Bank Files', '*.yaml')])
        if bank == '': return
        self.last_bankdir = Path(bank).parent
        self.menu_save(bank)
        
    def menu_exit(self, *_):
        if self.bedit.text.edit_modified():
            resp = msgbox.askyesnocancel("Exit", "Unsaved changes in bank - save?")
            if resp == True: self.menu_saveas()
            elif resp == None: return
        sys.exit()

    def menu_choosepreset(self, *_):
        sfont = filedlg.askopenfilename(initialdir=self.last_sfdir, initialfile=self.last_sfont,
                                       defaultextension='.sf2',
                                       filetypes=[('Soundfonts', '*.sf2')])
        if sfont == '': return
        self.last_sfdir = Path(sfont).parent
        sfrel = Path(sfont).relative_to(self.fp.sfdir).as_posix()
        if not (presets := self.fp.solo_soundfont(sfrel)):
            msgbox.showerror("Choose Preset", f"Unable to load {sf}")
            return
        self.last_sfont = sfont
        self.presetdlg.getpreset(sfrel, presets)

    def menu_midimon(self, *_):
        for i in self.midimon.msglist.get_children():
            self.midimon.msglist.delete(i)        
        self.midimon.show()

    def menu_fillscreen(self, *_):
        if self.master.wm_attributes('-fullscreen'):
            self.master.configure(menu=self.menu)
            self.master.wm_attributes('-fullscreen', False)
        else:
            self.master.configure(menu="")
            self.master.wm_attributes('-fullscreen', True)

    def load_bank(self, bank=''):
        if bank == '': bank = self.fp.bankdir / self.fp.currentbank
        self.set_text(str(bank), "", "loading bank")
        try:
            rawbank = (self.fp.bankdir / bank).read_text()
        except Exception as e:
            msgbox.showerror("Load Bank", f"Error loading {bank}:\n{str(e)}")
            return
        try:
            self.fp.load_bank(bank)
        except Exception as e:
            msgbox.showerror("Bank Error", f"Error in bank {bank}:\n{str(e)}")
        self.fp.update_config()
        self.lastfile = bank
        self.bedit.title(self.lastfile)
        self.bedit.text.delete('1.0', 'end')
        self.bedit.text.insert('1.0', rawbank)
        self.select_patch(0)
        self.parse_bank()
        self.bedit.text.edit_modified(False)
        
    def next_bank(self, *_):
        banks = sorted([b.relative_to(self.fp.bankdir)
                        for b in self.fp.bankdir.rglob('*.yaml')])
        if self.fp.currentbank in banks:
            bno = (banks.index(self.fp.currentbank) + 1) % len(banks)
        else:
            bno = 0
        self.load_bank(banks[bno])

    def parse_bank(self, *_):
        lastpatch = self.fp.patches[self.pno] if self.fp.patches else ''
        try:
            self.fp.load_bank(raw=self.bedit.text.get('1.0', 'end'))
        except Exception as e:
            self.bedit.text.configure(foreground='red')
            return False
        self.bedit.text.configure(foreground='black')
        self.patchmenu.delete(0, self.patchmenu.index('end'))
        for i, p in enumerate(self.fp.patches):
            self.patchmenu.add_command(label=p, command=lambda i=i: self.select_patch(i))
        if lastpatch in self.fp.patches:
            self.select_patch(self.fp.patches.index(lastpatch))
        elif self.pno < len(self.fp.patches):
            self.select_patch(self.pno)
        else:
            self.select_patch(0)
        return True


sys.excepthook = gui_excepthook
if len(sys.argv) > 1:
    cfgfile = Path(sys.argv[1])
else:
    cfgfile = Path('config/fluidpatcherconf.yaml')
app = MainWindow()
app.mainloop()
