#!/usr/bin/env python3
"""
Copyright (c) 2020 Bill Peterson

Description: a wxpython-based implementation of patcher.py for live editing/playing of bank files
"""

import wx
from os.path import relpath, join as joinpath
from sys import argv
from webbrowser import open as webopen
from mido import get_output_names, get_input_names
import patcher
from utils import netlink

DEFAULT_WIDTH  = 700
DEFAULT_HEIGHT = 600
APP_NAME = 'FluidPatcher'


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


class SoundfontBrowser(wx.Dialog):
    def __init__(self, parent, sf):
        super(SoundfontBrowser, self).__init__(parent, size=(400,650), title=sf,
                                                style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.sf = sf
        self.remoteLink = parent.remoteLink
        self.copypreset = ''

        self.presetlist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.presetlist.AppendColumn('Bank')
        self.presetlist.AppendColumn('Preset')
        self.presetlist.AppendColumn('Name')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.presetlist, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 15)
        vbox.Add(self.CreateSeparatedButtonSizer(wx.CLOSE), 0, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(vbox)

        if parent.remote_linked():
            reply = self.remoteLink.request(netlink.LOAD_SOUNDFONT, sf)
            for p in patcher.read_yaml(reply.body):
                self.presetlist.Append(("%03d:" % p.bank, "%03d:" % p.prog, p.name))
        else:
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
        if self.remoteLink:
            if not self.remoteLink.isconnected():
                self.EndModal(wx.CANCEL)
                return
            self.remoteLink.request(netlink.SELECT_SFPRESET, self.pno)
        else:
            pxr.select_sfpreset(self.pno)
        
    def onActivate(self, event):
        bank, prog = [self.presetlist.GetItemText(event.GetIndex(), x).strip(':') for x in (0, 1)]
        self.copypreset = ':'.join((self.sf, bank, prog))
        self.EndModal(wx.ID_OK)


class MainWindow(wx.Frame):
    def __init__(self):
        super(MainWindow, self).__init__(None, size=(700,600), title=APP_NAME)
                
# create menus
        fileMenu = wx.Menu()
        
        item = fileMenu.Append(wx.ID_OPEN, 'L&oad Bank...\tCtrl+O', 'Load bank file')
        self.Bind(wx.EVT_MENU, self.onOpen, item)
        
        item = fileMenu.Append(wx.ID_SAVE, '&Save Bank\tCtrl+S', 'Save current bank')
        self.Bind(wx.EVT_MENU, self.onSave, item)
        
        item = fileMenu.Append(wx.ID_SAVEAS, 'Save Bank &As...\tCtrl+Shift+S', 'Save bank file')
        self.Bind(wx.EVT_MENU, self.onSaveAs, item)
        
        item = fileMenu.Append(wx.ID_ANY, 'Open Sound&Font...', 'Open a soundfont and browse presets')
        self.Bind(wx.EVT_MENU, self.onOpenSoundfont, item)
        fileMenu.AppendSeparator()
        item = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q', 'Terminate the program')
        self.Bind(wx.EVT_MENU, self.onExit, item)

        toolsMenu = wx.Menu()
        self.linkmenuitem = toolsMenu.Append(wx.ID_ANY, '&Remote Link', 'Connect to and control a remote unit')
        self.Bind(wx.EVT_MENU, self.onRemoteLink, self.linkmenuitem)
        item = toolsMenu.Append(wx.ID_ANY, 'Browse &Plugins', 'View available LADSPA plugins')
        self.Bind(wx.EVT_MENU, self.onBrowsePlugins, item)
        item = toolsMenu.Append(wx.ID_ANY, '&MIDI ports', 'List available MIDI devices')
        self.Bind(wx.EVT_MENU, self.onListMIDI, item)
        toolsMenu.AppendSeparator()
        item = toolsMenu.Append(wx.ID_ANY, '&Settings...\tCtrl+,', 'Edit FluidPatcher configuration')
        self.Bind(wx.EVT_MENU, self.onSettings, item)
        
        helpMenu = wx.Menu()
        item = helpMenu.Append(wx.ID_ANY, '&Online Help', 'Open online help in a web browser')
        self.Bind(wx.EVT_MENU, lambda x: webopen('https://github.com/albedozero/fluidpatcher/wiki'), item)
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
        self.Bind(wx.EVT_TOOL, lambda x: self.choose_patch(x, -1), tool)
        tool = patchTool.AddTool(wx.ID_ANY, 'Next', wx.ArtProvider.GetBitmap(wx.ART_PLUS), 'Select next patch (F8)')
        tool.SetLongHelp('Select next patch')
        self.Bind(wx.EVT_TOOL, lambda x: self.choose_patch(x, 1), tool)
        self.patchlist = wx.Choice(patchTool)
        tool = patchTool.AddControl(self.patchlist, 'Patches')
        self.Bind(wx.EVT_CHOICE, self.choose_patch, self.patchlist)

        patchTool.Realize()        

# create window elements
        self.btxt = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_RICH|
                                            wx.TE_NOHIDESEL|wx.HSCROLL)
        fwf = wx.Font(wx.FontInfo().Family(wx.FONTFAMILY_TELETYPE))
        self.btxt.SetDefaultStyle(wx.TextAttr(wx.NullColour, font=fwf))

        self.Bind(wx.EVT_TEXT, self.onMod)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        self.Bind(wx.EVT_CLOSE, self.onExit)
        _icon = wx.Icon('images/gfl_logo.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        self.SetSize(size=wx.Size(DEFAULT_WIDTH, DEFAULT_HEIGHT))
        
        host = pxr.cfg.get('remotelink_host', 'x.x.x.x')
        port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)
            
        self.remoteLinkAddr = "%s:%d" % (host, port)
        self.remoteLink = None
        self.load_bankfile(pxr.cfg['currentbank'])

            
    def remote_linked(self):
        if self.remoteLink:
            if self.remoteLink.isconnected():
                return True
            self.remoteLink.close()
            self.remoteLink = None
            wx.MessageBox("Lost connection to %" % self.remoteLinkAddr, "Connection Lost", wx.OK|wx.ICON_ERROR)
            self.load_bankfile(self.currentfile)
            self.linkmenuitem.SetItemLabel("&Remote Link")
        return False
           
    def load_bankfile(self, file):
        if self.remote_linked():
            reply = self.remoteLink.request(netlink.LOAD_BANK, file)
            bank, patches = patcher.read_yaml(reply.body)
            rawbank = patcher.write_yaml(bank)
            host = self.remoteLinkAddr.split(':')[0]
            title = APP_NAME + ' - ' + file + '@' + host
        else:
            try:
                pxr.load_bank(file)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            self.currentfile = file
            f = open(joinpath(pxr.bankdir, self.currentfile))
            rawbank = f.read()
            f.close()
            patches = pxr.patch_name()
            title = APP_NAME + ' - ' + self.currentfile
        self.btxt.Clear()
        self.btxt.AppendText(rawbank)
        self.btxt.SetInsertionPoint(0)
        self.SetTitle(title)
        self.patchlist.Clear()
        for p in patches:
            self.patchlist.Append(p)
        self.ptot = len(patches)
        self.choose_patch(val=0)
            
    def choose_patch(self, event=None, val=''):
        if val == 0:
            self.pno = 0
            self.patchlist.SetSelection(0)
        elif val == 1 or val == -1:
            self.pno = (self.pno + val) % self.ptot
            self.patchlist.SetSelection(self.pno)
        else:
            n = self.patchlist.GetSelection()
            if n == wx.NOT_FOUND: return
            self.pno = n
        if self.remote_linked():
            reply = self.remoteLink.request(netlink.SELECT_PATCH, self.pno)
        else:
            warn = pxr.select_patch(self.pno)
        
    def onOpen(self, event):
        if self.remote_linked():
            reply = self.remoteLink.request(netlink.LIST_BANKS)
            banks = reply.body.split(',')
            bfile = wx.GetSingleChoice("Choose bank to load:", "Load Bank", banks)
            if bfile == '': return
        else:
            path = wx.FileSelector("Load Bank", pxr.bankdir, "", "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_OPEN)
            if path == '': return
            bfile = relpath(path, start=pxr.bankdir)
        self.load_bankfile(bfile)
        
    def onSave(self, event):
        self.onSaveAs(bfile=self.currentfile)
        
    def onSaveAs(self, event=None, bfile=''):
        rawbank = self.btxt.GetValue()
        try:
            patcher.read_yaml(rawbank)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return
        if self.remote_linked():
            bfile = wx.GetTextFromUser("Bank file to save:", "Save Bank", ".yaml")
            if bfile == '': return            
            reply = self.remoteLink.request(netlink.SAVE_BANK, patcher.write_yaml(bfile, rawbank))
            host, port = self.remoteLinkAddr.split(':')
            self.SetTitle(APP_NAME + ' - ' + bfile + '@' + host)
        else:
            if bfile == '':
                path = wx.FileSelector("Save Bank", pxr.bankdir, self.currentfile, "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_SAVE)
                if path == '': return
                bfile = replath(path, start=pxr.bankdir)
            try:
                pxr.save_bank(bfile, rawbank)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            self.currentfile = bfile
            self.SetTitle(APP_NAME + ' - ' + self.currentfile)

    def onMod(self, event):
        self.SetTitle(self.GetTitle().rstrip('*') + '*')
                
    def onOpenSoundfont(self, event):
        if self.remote_linked():
            reply = self.remoteLink.request(netlink.LIST_SOUNDFONTS)
            sfonts = reply.body.split(',')
            sfont = wx.GetSingleChoice("Choose Soundfont to Open:", "Open Soundfont", sfonts)
            if sfont == '': return        
        else:
            s = wx.FileSelector("Open Soundfont", pxr.sfdir, "", "*.sf2", "Soundfont (*.sf2)|*.sf2", wx.FD_OPEN)
            if s == '': return
            sfont = relpath(s, start=pxr.sfdir)
        sfbrowser = SoundfontBrowser(self, sfont)
        if sfbrowser.ShowModal() == wx.ID_OK:
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(wx.TextDataObject(sfbrowser.copypreset))
            wx.TheClipboard.Close()
        sfbrowser.Destroy()
        self.choose_patch()

    def onExit(self, event=None):
        self.Destroy()
        
    def onRemoteLink(self, event):
        if self.remote_linked():
            self.remoteLink.close()
            self.remoteLink = None
            self.load_bankfile(self.currentfile)
            self.linkmenuitem.SetItemLabel("&Remote Link")
        else:                
            addr = wx.GetTextFromUser("Network Address (host:port):", "Remote Link", self.remoteLinkAddr)
            if addr == '': return
            self.remoteLinkAddr = addr
            host, port = addr.split(':')
            passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
            try:
                self.remoteLink = netlink.Client(host, int(port), passkey)
                reply = self.remoteLink.request(netlink.SEND_STATE)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            if reply.type != netlink.REQ_OK:
                wx.MessageBox("Unable to connect to %s" % host, "Error", wx.OK|wx.ICON_ERROR)
                return
            wx.MessageBox("Connected to %s!" % host, "Connected", wx.OK)
            pxr.cfg['remotelink_host'] = host
            pxr.cfg['remotelink_port'] = int(port)
            pxr.write_config()
            
            bank, patches, bfile = patcher.read_yaml(reply.body)
            self.btxt.Clear()
            self.btxt.AppendText(patcher.write_yaml(bank))
            self.btxt.SetInsertionPoint(0)
            self.patchlist.Clear()
            for p in patches:
                self.patchlist.Append(p)
            self.patchlist.SetSelection(0)
            self.pno = 0
            self.ptot = len(patches)
            self.SetTitle(APP_NAME + ' - ' + bfile + '@' + host)
            self.linkmenuitem.SetItemLabel("&Disconnect")
            pxr.fluid.router_clear()

    def onBrowsePlugins(self, event):
        if self.remote_linked():
            plugins = self.remoteLink.request(netlink.LIST_PLUGINS).body
            tmsg = TextMsgDialog(plugins, "Plugins", "Available plugins on %s:" % self.remoteLinkAddr)
            tmsg.ShowModal()
            tmsg.Destroy()
        else:
            if not pxr.plugindir:
                pdir = wx.DirSelector("Select Plugins Directory")
                if pdir == '': return
                pxr.plugindir = pdir
                pxr.cfg['plugindir'] = pdir
                pxr.write_config()
            plugin = wx.FileSelector("Plugins", pxr.plugindir, "", "*.dll", "LADSPA plugin (*.dll)|*.dll")
            if plugin:
                wx.TheClipboard.Open()
                wx.TheClipboard.SetData(wx.TextDataObject(relpath(plugin, start=pxr.plugindir)))
                wx.TheClipboard.Close()

    def onListMIDI(self, event):
        if self.remote_linked():
            ports = self.remoteLink.request(netlink.LIST_PORTS).body
            caption = "MIDI ports on %s:" % self.remoteLinkAddr
        else:
            ports = "Inputs:\n  %s\nOutputs:\n  %s" % (
                '\n  '.join(get_input_names()),
                '\n  '.join(get_output_names()))
            caption = "Local MIDI ports:"
        tmsg = TextMsgDialog(ports, "MIDI Ports", caption)
        tmsg.ShowModal()
        tmsg.Destroy()

    def onSettings(self, event):
        f = open(pxr.cfgfile)
        rawcfg = f.read()
        f.close()
        tmsg = TextMsgDialog(rawcfg, "Settings", pxr.cfgfile, wx.OK|wx.CANCEL, edit=True, size=(500, 450))
        if tmsg.ShowModal() == wx.ID_OK:
            newcfg = tmsg.text.GetValue()
            try:
                pxr.write_config(newcfg)
            except patcher.PatcherError as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            wx.MessageBox("Configuration saved\nRestart needed to apply", "Success", wx.OK)
        tmsg.Destroy()

    def onAbout(self, event):
        msg = """
               Fluid Patcher v0.3
               
        Allows in-place editing and playing
           of FluidPatcher bank files.

                by Bill Peterson
                geekfunklabs.com
"""
        msg = wx.MessageDialog(self, msg, "About", wx.OK)
        msg.ShowModal()
        msg.Destroy()

    def onRefresh(self, event=None):
        rawbank = self.btxt.GetValue()
        try:
            patcher.read_yaml(rawbank)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return

        if self.remote_linked():
            reply = self.remoteLink.request(netlink.RECV_BANK, rawbank)
            lastpatch = self.patchlist.GetString(self.pno)
            patches = reply.body.split(',')
        else:
            lastpatch = pxr.patch_name(self.pno)
            pxr.load_bank(rawbank)
            patches = pxr.patch_names()
                        
        self.ptot = len(patches)
        self.patchlist.Clear()
        for p in patches:
            self.patchlist.Append(p)
        if lastpatch in patches:
            self.pno = patches.index(lastpatch)
        elif self.pno >= self.ptot:
            self.pno = 0
        self.patchlist.SetSelection(self.pno)
        self.choose_patch()
        
    def onKeyPress(self, event):
        if event.GetModifiers()<=0:
            if event.GetKeyCode() == wx.WXK_F5:
                self.onRefresh()
                return
            if event.GetKeyCode() == wx.WXK_F7:
                self.choose_patch(val=-1)
                return
            if event.GetKeyCode() == wx.WXK_F8:
                self.choose_patch(val=1)
                return
        event.Skip()
        
if __name__ == "__main__":
    if len(argv) > 1:
        cfgfile = argv[1]
    else:
        cfgfile = 'patcherconf.yaml'
    pxr = patcher.Patcher(cfgfile)

    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.MainLoop()
