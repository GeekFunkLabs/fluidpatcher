#!/usr/bin/env python3
"""
Description: a wxpython-based graphical implementation of patcher.py
              for composing/editing bank files or live playing
"""

WIDTH = 500
HEIGHT = 320
FONTSIZE = 24
PAD = 10
FILLSCREEN = False


import wx, sys, traceback, webbrowser
from pathlib import Path
import patcher

POLL_TIME = 25
APP_NAME = 'FluidPatcher'
MSG_TYPES = 'note', 'noteoff', 'kpress', 'cc', 'prog', 'pbend', 'cpress'
MSG_NAMES = "Note On", "Note Off", "Key Pressure", "Control Change", "Program Change", "Pitch Bend", "Aftertouch"


def gui_excepthook(etype, val, tb):
    # catch all unhandled exceptions
    # display the error in a message box
    s = traceback.format_exception(etype, val, tb)
    wx.MessageBox(''.join(s), "Error", wx.OK|wx.ICON_ERROR)


class ControlBoard(wx.Panel):

    def __init__(self, parent):
        super(ControlBoard, self).__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.onClick)
        
    def onSize(self, event):
        event.Skip()
        self.Refresh()
        
    def onPaint(self, event):
        w, h = self.GetClientSize()
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetFont(wx.Font(wx.FontInfo(FONTSIZE)))
        fh = dc.GetTextExtent('X')[1]
        h2 = fh * 3 + PAD * 4
        dc.Clear()
        dc.SetPen(wx.Pen(wx.BLACK, 5))
        dc.SetBrush(wx.Brush((0, 100, 255)))
        dc.DrawRectangle(0, 0, w, h2)
        dc.SetTextForeground(wx.WHITE)
        dc.SetClippingRegion(PAD, PAD, w - 2 * PAD, fh * 3 + PAD * 2)
        dc.DrawLabel(display[0], wx.Rect(PAD, PAD, w - 2 * PAD, fh))
        dc.DrawLabel(display[1], wx.Rect(PAD, fh * 1 + PAD * 2, w - 2 * PAD, fh))
        dc.DrawLabel(display[2], wx.Rect(PAD, fh * 2 + PAD * 3, w - 2 * PAD, fh), wx.ALIGN_RIGHT)
        dc.DestroyClippingRegion()
        
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(wx.Font(wx.FontInfo(int(FONTSIZE * 0.6))))
        for i, name, symbol, accel, color in ((0, 'Prev', '-', '[F3]', (255, 255, 0)),
                                              (1, 'Next', '+', '[F4]', (0, 255, 0)),
                                              (2, 'Bank', '>', '[F6]', (255, 100, 100))):
            dc.SetPen(wx.Pen(color, 0))
            dc.SetBrush(wx.Brush(color))
            dc.DrawRectangle(int(w / 3 * i), h2, int(w / 3 + 1), h - h2)
            dc.DrawLabel(symbol, wx.Rect(int(w / 3 * (i + 0.5)), int((h + h2) / 2), 1, 1), wx.ALIGN_CENTER)
            if h > (fh + PAD) * 5 and w > (fh + PAD) * 4:
                dc.DrawLabel(name, wx.Rect(int(w / 3 * i + PAD), h2 + PAD, 1, 1))
                dc.DrawLabel(accel, wx.Rect(int(w / 3 * (i + 1) - PAD), h - PAD, 1, 1), wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        
        self.h2 = h2
        self.w = w
        
    def onClick(self, event):
        event.Skip()
        if event.LeftDown() and event.GetY() > self.h2:
            if event.GetX() < self.w / 3 * 1:
                main.select_patch(pno=(main.pno - 1) % len(pxr.patches))
            elif event.GetX() < self.w / 3 * 2:
                main.select_patch(pno=(main.pno + 1) % len(pxr.patches))
            elif event.GetX() < self.w / 3 * 3:
                main.next_bankfile()


class TextCtrlDialog(wx.Dialog):

    def __init__(self, parent, text, title, caption='', flags=wx.CLOSE, edit=False, **kwargs):
        super(TextCtrlDialog, self).__init__(parent, title=title,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER, **kwargs)
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_RICH|wx.HSCROLL)
        if edit:
            fwf = wx.Font(wx.FontInfo().Family(wx.FONTFAMILY_TELETYPE))
            self.text.SetDefaultStyle(wx.TextAttr(wx.NullColour, font=fwf))
        self.text.WriteText(text)
        self.text.SetInsertionPoint(0)
        self.text.SetEditable(edit)
        vbox = wx.BoxSizer(wx.VERTICAL)
        if caption:
            self.caption = wx.StaticText(self, label=caption)
            vbox.Add(self.caption, 0, wx.ALL|wx.ALIGN_LEFT, 10)
        vbox.Add(self.text, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        x=self.CreateStdDialogButtonSizer(flags)
        vbox.Add(x, 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)


class MidiMonitor(wx.Dialog):

    def __init__(self, parent):
        super(MidiMonitor, self).__init__(parent, title='MIDI Monitor', size=(350, 500),
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.msglist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.msglist.AppendColumn('Type')
        self.msglist.AppendColumn('Channel')
        self.msglist.AppendColumn('Data')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.msglist, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateStdDialogButtonSizer(wx.CLOSE), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)
        self.msglist.SetColumnWidth(0, 120)
        self.msglist.SetColumnWidth(1, 60)
        self.msglist.SetColumnWidth(2, 100)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        self.Bind(wx.EVT_SHOW, self.onHide)

    def onHide(self, event):
        event.Skip()
        if not event.IsShown():
            self.timer.Stop()
            self.msglist.DeleteAllItems()
            
    def onTimer(self, event):
        if midimsgs:
            for msg in midimsgs:
                self.msglist.Append(msg)
            midimsgs.clear()
            n = self.msglist.GetItemCount()
            pos = self.msglist.GetItemPosition(n - 1)
            self.msglist.ScrollList(0, pos.y)

    
class SoundfontBrowser(wx.Dialog):

    def __init__(self, parent, sf):
        super(SoundfontBrowser, self).__init__(parent, title=str(sf), size=(400, 650),
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.sf = sf
        self.copypreset = ''

        self.presetlist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.presetlist.AppendColumn('Bank')
        self.presetlist.AppendColumn('Program')
        self.presetlist.AppendColumn('Name')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.presetlist, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateStdDialogButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)

        pxr.load_soundfont(sf)
        for p in pxr.sfpresets:
            self.presetlist.Append((f"{p.bank:03d}:", f"{p.prog:03d}:", p.name))
        
        self.presetlist.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.presetlist.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.presetlist.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.preset_select, self.presetlist)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onActivate, self.presetlist)
        self.preset_select(val=0)
        
    def preset_select(self, event=None, val=''):
        if val == 0:
            self.pno = 0
            self.presetlist.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            return
        self.pno = self.presetlist.GetNextSelected(-1)
        if self.pno < 0: return
        warn = pxr.select_sfpreset(self.pno)
        if warn:
            wx.MessageBox('\n'.join(warn), "Warning", wx.OK|wx.ICON_WARNING)
        bank, prog = [self.presetlist.GetItemText(event.GetIndex(), x).strip(':') for x in (0, 1)]
        self.copypreset = ':'.join((self.sf.as_posix(), bank, prog))
        
    def onActivate(self, event):
        self.EndModal(wx.ID_OK)


class MainWindow(wx.Frame):

    def __init__(self):
        super(MainWindow, self).__init__(None, title=APP_NAME, size=(WIDTH, HEIGHT))

        fileMenu = wx.Menu()
        x = fileMenu.Append(wx.ID_NEW, '&New Bank\tCtrl+N', 'Start a new bank')
        self.Bind(wx.EVT_MENU, self.onNew, x)
        x = fileMenu.Append(wx.ID_OPEN, 'L&oad Bank...\tCtrl+O', 'Load bank file')
        self.Bind(wx.EVT_MENU, self.onOpen, x)
        x = fileMenu.Append(wx.ID_SAVE, '&Save Bank\tCtrl+S', 'Save current bank')
        self.Bind(wx.EVT_MENU, self.onSave, x)
        x = fileMenu.Append(wx.ID_SAVEAS, 'Save Bank &As...\tCtrl+Shift+S', 'Save bank file')
        self.Bind(wx.EVT_MENU, self.onSaveAs, x)
        fileMenu.AppendSeparator()
        x = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q', 'Terminate the program')
        self.Bind(wx.EVT_MENU, self.onExit, x)

        self.patchMenu = wx.Menu()
        toolsMenu = wx.Menu()
        x = toolsMenu.Append(wx.ID_ANY, 'Edit &Bank\tCtrl+B', 'Edit the current bank')
        self.Bind(wx.EVT_MENU, self.onEditBank, x)
        x = toolsMenu.Append(wx.ID_ANY, 'Choose &Preset\tCtrl+P', 'Choose preset from a soundfont')
        self.Bind(wx.EVT_MENU, self.onChoosePreset, x)
        x = toolsMenu.Append(wx.ID_ANY, '&MIDI Monitor', 'Monitor incoming MIDI messages')
        self.Bind(wx.EVT_MENU, self.onMidiMon, x)
        x = toolsMenu.Append(wx.ID_ANY, '&Fill Screen\tF11', 'Fill the screen')
        self.Bind(wx.EVT_MENU, self.onFillScreen, x)
        toolsMenu.AppendSeparator()
        x = toolsMenu.Append(wx.ID_ANY, '&Settings...\tCtrl+,', 'Edit FluidPatcher configuration')
        self.Bind(wx.EVT_MENU, self.onSettings, x)
        
        helpMenu = wx.Menu()
        x = helpMenu.Append(wx.ID_ANY, '&Online Help', 'Open online help in a web browser')
        self.Bind(wx.EVT_MENU, lambda _: webbrowser.open('https://github.com/albedozero/fluidpatcher/wiki'), x)
        x = helpMenu.Append(wx.ID_ABOUT, '&About', 'Information about this program')
        self.Bind(wx.EVT_MENU, self.onAbout, x)

        self.menubar = wx.MenuBar()
        self.menubar.Append(fileMenu, '&File')
        self.menubar.Append(self.patchMenu, '&Patches')
        self.menubar.Append(toolsMenu, '&Tools')
        self.menubar.Append(helpMenu, '&Help')
        self.SetMenuBar(self.menubar)

        self.ctrlboard = ControlBoard(self)
        self.bedit = TextCtrlDialog(self, '', "Bank Editor", ' ', flags=wx.APPLY|wx.CLOSE, edit=True, size=(500, 450))
        self.midimon = MidiMonitor(self)
        self.bedit.Bind(wx.EVT_TEXT, self.onMod)
        self.bedit.Bind(wx.EVT_BUTTON, self.onBankEditButton)
        self.bedit.Bind(wx.EVT_CHAR_HOOK, self.onKeyPressDialog)
        self.midimon.Bind(wx.EVT_CHAR_HOOK, self.onKeyPressDialog)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        self.Bind(wx.EVT_CLOSE, self.onExit)        
        _icon = wx.Icon('assets/gfl_logo.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        if FILLSCREEN: self.onFillScreen()
        
        self.lastdir = dict(bank=pxr.bankdir, sf2=pxr.sfdir)
        self.onNew()
        if pxr.currentbank: self.load_bankfile(str(pxr.currentbank))

    def listener(self, msg):
        if hasattr(msg, 'val'):
            if hasattr(msg, 'patch') and pxr.patches:
                if msg.patch == 'select':
                    self.select_patch(pno=int(msg.val))
                elif msg.val > 0:
                    self.select_patch(pno=(self.pno + msg.patch) % len(pxr.patches))
            elif hasattr(msg, 'lcdwrite'):
                if hasattr(msg, 'format'):
                    val = format(msg.val, msg.format)
                    display[2] = f"{msg.lcdwrite} {val}"
                else:
                    display[2] = msg.lcdwrite
                self.ctrlboard.Refresh()
        elif hasattr(self.midimon, 'timer') and self.midimon.timer.IsRunning() and msg.type in MSG_TYPES:
            t = MSG_TYPES.index(msg.type)
            if t < 3:
                octave = int(msg.par1 / 12) - 1
                note = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')[msg.par1 % 12]
                midimsgs.append((MSG_NAMES[t], str(msg.chan + 1), f"{msg.par1} ({note}{octave})={msg.par2}"))
            elif t < 4:
                midimsgs.append((MSG_NAMES[t], str(msg.chan + 1), f"{msg.par1}={msg.par2}"))
            elif t < 7:
                midimsgs.append((MSG_NAMES[t], str(msg.chan + 1), str(msg.par1)))

    def load_bankfile(self, bfile=''):
        display[:] = [bfile, "", "loading patches"]
        self.ctrlboard.Refresh()
        self.ctrlboard.Update()
        try:
            rawbank = pxr.load_bank(bfile)
        except Exception as e:
            wx.MessageBox(str(e), f"Error Loading {bfile}", wx.OK|wx.ICON_ERROR)
            display[0] = self.currentfile
            self.select_patch(pno=self.pno, force=True)
            return False
        pxr.write_config()
        self.bedit.text.Clear()
        self.bedit.text.AppendText(rawbank)
        self.bedit.text.SetInsertionPoint(0)
        self.bedit.caption.SetLabel(bfile)
        for i in self.patchMenu.GetMenuItems():
            self.patchMenu.Delete(i)
        for p in pxr.patches:
            x = self.patchMenu.Append(wx.ID_ANY, p)
            self.Bind(wx.EVT_MENU, self.select_patch, x)
        self.currentfile = bfile
        self.select_patch(pno=0, force=True)
        return True

    def next_bankfile(self):
        if pxr.currentbank in pxr.banks:
            bno = (pxr.banks.index(pxr.currentbank) + 1 ) % len(pxr.banks)
        else:
            bno = 0
        self.load_bankfile(str(pxr.banks[bno]))

    def parse_bank(self, text=''):
        lastpatch = pxr.patches[self.pno] if pxr.patches else ''
        try:
            pxr.load_bank(raw=text or self.bedit.text.GetValue())
        except Exception as e:
            wx.MessageBox(str(e), "Error Reading Bank", wx.OK|wx.ICON_ERROR)
            return False
        for i in self.patchMenu.GetMenuItems():
            self.patchMenu.Delete(i)
        for p in pxr.patches:
            x = self.patchMenu.Append(wx.ID_ANY, p)
            self.Bind(wx.EVT_MENU, self.select_patch, x)
        if lastpatch in pxr.patches:
            self.select_patch(pno=pxr.patches.index(lastpatch), force=True)
        elif self.pno < len(pxr.patches):
            self.select_patch(pno=self.pno, force=True)
        else:
            self.select_patch(pno=0, force=True)
        return True
        
    def select_patch(self, event=None, pno=0, force=False):
        if not pxr.patches:
            self.pno = 0
            display[1:] = "No Patches", "patch 0/0"
            warn = pxr.apply_patch(None)
        else:
            if event:
                p = self.patchMenu.FindItemById(event.GetId()).GetItemLabelText()
                self.pno = pxr.patches.index(p)
            elif pno == self.pno and not force:
                return
            else:
                self.pno = pno
            warn = pxr.apply_patch(self.pno)
            display[1:] = pxr.patches[self.pno], f"patch {self.pno + 1}/{len(pxr.patches)}"
        self.ctrlboard.Refresh()
        if warn: wx.MessageBox('\n'.join(warn), "Warning", wx.OK|wx.ICON_WARNING)

    def onNew(self, event=None):
        if self.GetTitle().endswith('*'):
            resp = wx.MessageBox("Unsaved changes in bank - close?", "New", wx.ICON_WARNING|wx.OK|wx.CANCEL)
            if resp != wx.OK:
                return
        self.currentfile = ''
        self.pno = 0
        self.bedit.text.Clear()
        self.bedit.text.AppendText(" ")
        self.bedit.text.SetInsertionPoint(0)
        self.parse_bank('patches: {}')
        display[0] = "(Untitled)"
        self.bedit.caption.SetLabel("(Untitled)")
        self.ctrlboard.Refresh()

    def onOpen(self, event):
        bank = wx.FileSelector("Load Bank", str(self.lastdir['bank']), "", "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_OPEN)
        if bank == '': return
        self.lastdir['bank'] = Path(bank).parent
        self.load_bankfile(str(Path(bank).relative_to(pxr.bankdir)))

    def onSave(self, event):
        self.onSaveAs(bfile=self.currentfile)

    def onSaveAs(self, event=None, bfile=''):
        if not self.parse_bank():
            return
        if bfile == '':
            bank = wx.FileSelector("Save Bank", str(self.lastdir['bank']), "", "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            if bank == '': return
            self.lastdir['bank'] = Path(bank).parent
            bfile = str(Path(bank).relative_to(pxr.bankdir))
        try:
            pxr.save_bank(bfile, self.bedit.text.GetValue())
        except Exception as e:
            wx.MessageBox(str(e), "Error Saving Bank", wx.OK|wx.ICON_ERROR)
            return
        pxr.write_config()
        display[0] = bfile
        self.bedit.caption.SetLabel(bfile)
        self.currentfile = bfile
        self.ctrlboard.Refresh()

    def onExit(self, event=None):
        if isinstance(event, wx.CloseEvent) and not event.CanVeto():
            self.Destroy()
        if self.bedit.caption.GetLabel().endswith('*'):
            resp = wx.MessageBox("Unsaved changes in bank - quit?", "Exit", wx.ICON_WARNING|wx.OK|wx.CANCEL)
            if resp != wx.OK:
                if hasattr(event, 'Veto'): event.Veto()
                return
        self.Destroy()
        self.bedit.Destroy()
        self.midimon.Destroy()

    def onFillScreen(self, event=None):
        if self.GetMenuBar() == self.menubar:
            self.SetMenuBar(None)
            self.bedit.Show(False)
            self.midimon.Show(False)
            self.Maximize()
        else:
            self.SetMenuBar(self.menubar)
            self.Maximize(False)

    def onEditBank(self, event):
        self.bedit.Show()
        self.bedit.Raise()

    def onChoosePreset(self, event):
        sf = wx.FileSelector("Open Soundfont", str(self.lastdir['sf2']), "", "*.sf2", "Soundfont (*.sf2)|*.sf2", wx.FD_OPEN)
        if sf == '': return
        sfrel = Path(sf).relative_to(pxr.sfdir)
        if not pxr.load_soundfont(sf):
            wx.MessageBox(f"Unable to load {str(sfrel)}", "Error", wx.OK|wx.ICON_ERROR)
            return
        self.lastdir['sf2'] = Path(sf).parent
        sfbrowser = SoundfontBrowser(self, sfrel)
        if sfbrowser.ShowModal() == wx.ID_OK and self.bedit.IsShown():
            self.bedit.text.WriteText(sfbrowser.copypreset)
        sfbrowser.Destroy()
        pxr.load_bank()
        self.select_patch(pno=self.pno, force=True)

    def onMidiMon(self, event):
        self.midimon.timer.Start(100)
        self.midimon.Show()
        self.midimon.Raise()

    def onSettings(self, event):
        rawcfg = pxr.read_config()
        tmsg = TextCtrlDialog(self, rawcfg, "Settings", cfgfile, wx.OK|wx.CANCEL, edit=True, size=(500, 450))
        if tmsg.ShowModal() == wx.ID_OK:
            newcfg = tmsg.text.GetValue()
            try:
                pxr.write_config(newcfg)
            except Exception as e:
                wx.MessageBox(str(e), "Error Saving Settings", wx.OK|wx.ICON_ERROR)
                return
            wx.MessageBox("Configuration saved!\nRestart may be needed for some settings to apply.", "Success", wx.OK)
        tmsg.Destroy()

    def onAbout(self, event):
        msg = f"""
FluidPatcher v{patcher.VERSION}
github.com/albedozero/fluidpatcher

by Bill Peterson
geekfunklabs.com
"""
        wx.MessageBox(msg, "About", wx.OK)

    def onMod(self, event):
        t = self.bedit.caption.GetLabel()
        self.bedit.caption.SetLabel(t.rstrip('*') + '*')

    def onKeyPress(self, event):
        if event.HasAnyModifiers():
            event.Skip()
        else:
            if event.GetKeyCode() == wx.WXK_F3:
                self.select_patch(pno=(self.pno - 1) % len(pxr.patches))
            elif event.GetKeyCode() == wx.WXK_F4:
                self.select_patch(pno=(self.pno + 1) % len(pxr.patches))
            elif event.GetKeyCode() == wx.WXK_F6: self.next_bankfile()
            elif event.GetKeyCode() == wx.WXK_F11: self.onFillScreen()
            else: event.Skip()

    def onKeyPressDialog(self, event):
        if event.HasAnyModifiers():
            if event.GetModifiers() == wx.MOD_CONTROL:
                if event.GetKeyCode() == ord('N'): self.onNew(event)
                elif event.GetKeyCode() == ord('O'): self.onOpen(event)
                elif event.GetKeyCode() == ord('S'): self.onSave(event)
                elif event.GetKeyCode() == ord('Q'): self.onExit(event)
                elif event.GetKeyCode() == ord('B'): self.onEditBank(event)
                elif event.GetKeyCode() == ord('P'): self.onChoosePreset(event)
                elif event.GetKeyCode() == ord(','): self.onSettings(event)
                else: event.Skip()
            elif event.GetModifiers() == wx.MOD_CONTROL | wx.MOD_SHIFT:
                if event.GetKeyCode() == ord('S'): self.onSaveAs(event)
                else: event.Skip()
            else: event.Skip()
        else:
            self.onKeyPress(event)

    def onBankEditButton(self, event):
        event.Skip()
        if event.GetEventObject().GetLabelText() == 'Apply':
            self.parse_bank()


if __name__ == "__main__":
    app = wx.App()
    sys.excepthook = gui_excepthook
    midimsgs = []
    display = ["", "", ""]
    cfgfile = sys.argv[1] if len(sys.argv) > 1 else 'fluidpatcherconf.yaml'
    pxr = patcher.Patcher(cfgfile)
    main = MainWindow()
    pxr.set_midimessage_callback(main.listener)
    main.Show()
    app.MainLoop()
