#!/usr/bin/env python3
"""
Description: a wxpython-based implementation of patcher.py
              for live editing/playing of bank files
              or remotely connecting to a squishbox/headlesspi for editing
"""

import wx, mido, sys, webbrowser
from pathlib import Path
import patcher

APP_NAME = 'FluidPatcher'
POLL_TIME = 25

MSG_TYPES = 'note', 'noteoff', 'cc', 'kpress', 'prog', 'pbend', 'cpress'
MSG_NAMES = "Note On", "Note Off", "Control Change", "Key Pressure", "Program Change", "Pitch Bend", "Aftertouch"

class TextMsgDialog(wx.Dialog):
    def __init__(self, text, title, caption='', flags=wx.CLOSE, edit=False, **kwargs):
        super(TextMsgDialog, self).__init__(None, title=title,
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
            msg = wx.StaticText(self, label=caption)
            vbox.Add(msg, 0, wx.ALL|wx.ALIGN_LEFT, 10)
        vbox.Add(self.text, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateSeparatedButtonSizer(flags), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)


class MidiMonitor(wx.Dialog):
    def __init__(self, hook):
        super(MidiMonitor, self).__init__(None, title='MIDI Monitor', size=(350, 500),
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.hook = hook
        msglist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        msglist.AppendColumn('Channel')
        msglist.AppendColumn('Type')
        msglist.AppendColumn('Data')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(msglist, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)
        msglist.SetColumnWidth(0, 60)
        msglist.SetColumnWidth(1, 120)
        msglist.SetColumnWidth(2, 100)
        self.hook.monitor = msglist


class SoundfontBrowser(wx.Dialog):
    def __init__(self, sf):
        super(SoundfontBrowser, self).__init__(None, title=sf, size=(400, 650),
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.sf = sf
        self.copypreset = ''

        self.presetlist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.presetlist.AppendColumn('Bank')
        self.presetlist.AppendColumn('Preset')
        self.presetlist.AppendColumn('Name')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.presetlist, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)

        pxr.load_soundfont(sf)
        for p in pxr.sfpresets:
            self.presetlist.Append(("%03d:" % p.bank, "%03d:" % p.prog, p.name))
        
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
        self.copypreset = ':'.join((self.sf, bank, prog))
        
    def onActivate(self, event):
        self.EndModal(wx.ID_OK)


class MainWindow(wx.Frame):
    def __init__(self):
        super(MainWindow, self).__init__(None, title=APP_NAME, size=(700, 600))
                
        # create menus
        fileMenu = wx.Menu()
        
        item = fileMenu.Append(wx.ID_NEW, '&New Bank\tCtrl+N', 'Start a new bank')
        self.Bind(wx.EVT_MENU, self.onNew, item)
        
        item = fileMenu.Append(wx.ID_OPEN, 'L&oad Bank...\tCtrl+O', 'Load bank file')
        self.Bind(wx.EVT_MENU, self.onOpen, item)
        
        item = fileMenu.Append(wx.ID_SAVE, '&Save Bank\tCtrl+S', 'Save current bank')
        self.Bind(wx.EVT_MENU, self.onSave, item)
        
        item = fileMenu.Append(wx.ID_SAVEAS, 'Save Bank &As...\tCtrl+Shift+S', 'Save bank file')
        self.Bind(wx.EVT_MENU, self.onSaveAs, item)
        
        fileMenu.AppendSeparator()
        item = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q', 'Terminate the program')
        self.Bind(wx.EVT_MENU, self.onExit, item)

        toolsMenu = wx.Menu()
        item = toolsMenu.Append(wx.ID_ANY, 'Choose &Preset...\tCtrl+P', 'Choose preset from a soundfont')
        self.Bind(wx.EVT_MENU, self.onChoosePreset, item)
        item = toolsMenu.Append(wx.ID_ANY, 'Browse P&lugins', 'View available LADSPA plugins')
        self.Bind(wx.EVT_MENU, self.onBrowsePlugins, item)
        item = toolsMenu.Append(wx.ID_ANY, '&MIDI Monitor', 'Monitor incoming MIDI messages')
        self.Bind(wx.EVT_MENU, self.onMidiMon, item)
        toolsMenu.AppendSeparator()
        item = toolsMenu.Append(wx.ID_ANY, '&Settings...\tCtrl+,', 'Edit FluidPatcher configuration')
        self.Bind(wx.EVT_MENU, self.onSettings, item)
        
        helpMenu = wx.Menu()
        item = helpMenu.Append(wx.ID_ANY, '&Online Help', 'Open online help in a web browser')
        self.Bind(wx.EVT_MENU, lambda x: webbrowser.open('https://github.com/albedozero/fluidpatcher/wiki'), item)
        item = helpMenu.Append(wx.ID_ABOUT, '&About', 'Information about this program')
        self.Bind(wx.EVT_MENU, self.onAbout, item)

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, '&File')
        menuBar.Append(toolsMenu, '&Tools')
        menuBar.Append(helpMenu, '&Help')
        self.SetMenuBar(menuBar)

        # toolbar
        patchTool = self.CreateToolBar()
        tool = patchTool.AddTool(wx.ID_REFRESH, 'Refresh', wx.ArtProvider.GetBitmap(wx.ART_REDO), 'Refresh patches (F5)')
        tool.SetLongHelp('Refresh patches from editor text')
        self.Bind(wx.EVT_TOOL, self.onRefresh, tool)
        tool = patchTool.AddTool(wx.ID_ANY, 'Prev', wx.ArtProvider.GetBitmap(wx.ART_MINUS), 'Select previous patch (F7)')
        tool.SetLongHelp('Select previous patch')
        self.Bind(wx.EVT_TOOL, lambda x: self.choose_patch(inc=-1), tool)
        tool = patchTool.AddTool(wx.ID_ANY, 'Next', wx.ArtProvider.GetBitmap(wx.ART_PLUS), 'Select next patch (F8)')
        tool.SetLongHelp('Select next patch')
        self.Bind(wx.EVT_TOOL, lambda x: self.choose_patch(inc=1), tool)
        self.patchlist = wx.Choice(patchTool)
        tool = patchTool.AddControl(self.patchlist, 'Patches')
        self.Bind(wx.EVT_CHOICE, self.choose_patch, self.patchlist)

        patchTool.Realize()        

        # create window elements, bindings
        self.btxt = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_RICH|
                                            wx.TE_NOHIDESEL|wx.HSCROLL)
        fwf = wx.Font(wx.FontInfo().Family(wx.FONTFAMILY_TELETYPE))
        self.btxt.SetDefaultStyle(wx.TextAttr(wx.NullColour, font=fwf))

        self.Bind(wx.EVT_TEXT, self.onMod)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        self.Bind(wx.EVT_CLOSE, self.onExit)
        
        _icon = wx.Icon('assets/gfl_logo.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        
        self.load_bankfile(str(pxr.currentbank))

    def listener(self, msg):
        if hasattr(msg, 'val'):
            pass
        else:
            if getattr(self, 'monitor', None):
                if msg.type in MSG_TYPES[0:5]:
                    self.monitor.Append((str(msg.chan + 1), MSG_NAMES[MSG_TYPES.index(msg.type)], f"{msg.par1}={msg.par2}"))
                else:
                    self.monitor.Append((str(msg.chan + 1), MSG_NAMES[MSG_TYPES.index(msg.type)], str(msg.par1)))
                self.monitor.ScrollList(0, 99)


    def load_bankfile(self, bfile=''):
        try:
            rawbank = pxr.load_bank(bfile)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return
        pxr.write_config()
        title = f"{APP_NAME} - {bfile}"
        self.currentfile = bfile
        self.btxt.Clear()
        self.btxt.AppendText(rawbank)
        self.btxt.SetInsertionPoint(0)
        self.SetTitle(title)
        self.patchlist.Clear()
        for p in pxr.patches:
            self.patchlist.Append(p)
        self.choose_patch()

    def choose_patch(self, event=None, inc=0, pno=0):
        if event:
            n = self.patchlist.GetSelection()
            if n == wx.NOT_FOUND: return
            self.pno = n
        elif inc:
            self.pno = (self.pno + inc) % len(pxr.patches)
            self.patchlist.SetSelection(self.pno)
        else:
            self.pno = pno
            self.patchlist.SetSelection(pno)
        warn = pxr.select_patch(self.pno)
        if warn: wx.MessageBox('\n'.join(warn), "Warning", wx.OK|wx.ICON_WARNING)

    def onNew(self, event):
        if self.GetTitle().endswith('*'):
            resp = wx.MessageBox("Unsaved changes in bank - close anyway?", "New", wx.ICON_WARNING|wx.OK|wx.CANCEL)
            if resp != wx.OK:
                return
        self.btxt.Clear()        
        self.btxt.AppendText(" ")
        self.btxt.SetInsertionPoint(0)
        self.patchlist.Clear()
        self.pno = 0
        self.currentfile = ''
        self.SetTitle(f"{APP_NAME} - (Untitled)")

    def onOpen(self, event):
        path = wx.FileSelector("Load Bank", str(pxr.bankdir), "", "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_OPEN)
        if path == '': return
        self.load_bankfile(str(Path(path).relative_to(pxr.bankdir)))

    def onSave(self, event):
        self.onSaveAs(bfile=self.currentfile)

    def onSaveAs(self, event=None, bfile=''):
        if not self.onRefresh():
            return
        if bfile == '':
            path = wx.FileSelector("Save Bank", str(pxr.bankdir), self.currentfile, "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            if path == '': return
            bfile = str(Path(path).relative_to(pxr.bankdir))
        try:
            pxr.save_bank(bfile, self.btxt.GetValue())
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return
        pxr.write_config()
        self.SetTitle(f"{APP_NAME} - {bfile}")
        self.currentfile = bfile

    def onExit(self, event=None):
        if isinstance(event, wx.CloseEvent) and not event.CanVeto():
            self.Destroy()
        if self.GetTitle().endswith('*'):
            resp = wx.MessageBox("Unsaved changes in bank - quit anyway?", "Exit", wx.ICON_WARNING|wx.OK|wx.CANCEL)
            if resp != wx.OK:
                if hasattr(event, 'Veto'): event.Veto()
                return
        self.Destroy()

    def onChoosePreset(self, event):
        sf = wx.FileSelector("Open Soundfont", str(pxr.sfdir), "", "*.sf2", "Soundfont (*.sf2)|*.sf2", wx.FD_OPEN)
        if sf == '': return
        sfbrowser = SoundfontBrowser(str(Path(sf).relative_to(pxr.sfdir)))
        if sfbrowser.ShowModal() == wx.ID_OK:
            self.btxt.WriteText(sfbrowser.copypreset)
        sfbrowser.Destroy()
        self.choose_patch(pno=self.pno)

    def onBrowsePlugins(self, event):
        if not pxr.plugindir:
            pdir = wx.DirSelector("Select Plugins Directory")
            if pdir == '': return
            pxr.cfg['plugindir'] = Path(pdir)
            pxr.write_config()
        plugin = wx.FileSelector("Plugins", str(pxr.plugindir), "", "*.dll", "LADSPA plugin (*.dll)|*.dll")
        if plugin:
            self.btxt.WriteText(str(Path(plugin).relative_to(pxr.plugindir)))

    def onMidiMon(self, event):
        midimon = MidiMonitor(self)
        midimon.ShowModal()
        midimon.Destroy()

    def onSettings(self, event):
        rawcfg = pxr.read_config()
        tmsg = TextMsgDialog(rawcfg, "Settings", str(pxr.cfgfile), wx.OK|wx.CANCEL, edit=True, size=(500, 450))
        if tmsg.ShowModal() == wx.ID_OK:
            newcfg = tmsg.text.GetValue()
            try:
                pxr.write_config(newcfg)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            wx.MessageBox("Configuration saved!\nRestart may be needed for some settings to apply.", "Success", wx.OK)
        tmsg.Destroy()

    def onAbout(self, event):
        msg = f"""
FluidPatcher v{patcher.VERSION}

by Bill Peterson
geekfunklabs.com
"""
        wx.MessageBox(msg, "About", wx.OK)

    def onRefresh(self, event=None):
        lastpatch = pxr.patches[self.pno]
        try:
            pxr.load_bank(raw=self.btxt.GetValue())
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return False
        self.patchlist.Clear()
        for p in pxr.patches:
            self.patchlist.Append(p)
        if lastpatch in pxr.patches:
            self.pno = pxr.patches.index(lastpatch)
        elif self.pno >= len(pxr.patches):
            self.pno = 0
        self.patchlist.SetSelection(self.pno)
        self.choose_patch(pno=self.pno)
        return True
        
    def onMod(self, event):
        self.SetTitle(self.GetTitle().rstrip('*') + '*')

    def onKeyPress(self, event):
        if event.GetModifiers()<=0:
            if event.GetKeyCode() == wx.WXK_F5:
                self.onRefresh()
                return
            if event.GetKeyCode() == wx.WXK_F7:
                self.choose_patch(inc=-1)
                return
            if event.GetKeyCode() == wx.WXK_F8:
                self.choose_patch(inc=1)
                return
        event.Skip()
        
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cfgfile = sys.argv[1]
    else:
        cfgfile = 'fluidpatcherconf.yaml'
    pxr = patcher.Patcher(cfgfile)

    app = wx.App()
    main = MainWindow()
    pxr.set_midimessage_callback(main.listener)
    main.Show()
    app.MainLoop()
