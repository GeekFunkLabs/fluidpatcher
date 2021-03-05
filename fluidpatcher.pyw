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

APP_NAME = 'FluidPatcher'
POLL_TIME = 25

def remote_link_request(type, body=''):
    try:
        reply = remote.link.request(type, body)
    except:
        reply = None
    if not reply or reply.type == netlink.NO_COMM:
        wx.MessageBox("Lost connection to %s" % remote.host, "Connection Lost", wx.OK|wx.ICON_ERROR)
        main.remote_disconnect()
        return None
    elif reply.type == netlink.REQ_ERROR:
        wx.MessageBox(reply.body, "Error", wx.OK|wx.ICON_ERROR)
        return None
    else:
        if reply.body == '':
            return reply.body
        else:
            return patcher.read_yaml(reply.body)


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

        if remote.link:
            response = remote_link_request(netlink.LOAD_SOUNDFONT, sf)
            if response == None: self.EndModal(wx.CANCEL)
            for p in response:
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
        if remote.link:
            response = remote_link_request(netlink.SELECT_SFPRESET, self.pno)
            if response == None: self.EndModal(wx.CANCEL)
            if response:
                warn = patcher.read_yaml(response)
                wx.MessageBox('\n'.join(warn), "Warning", wx.OK|wx.ICON_WARNING)
        else:
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
        item = toolsMenu.Append(wx.ID_ANY, '&MIDI ports', 'List available MIDI devices')
        self.Bind(wx.EVT_MENU, self.onListMIDI, item)
        toolsMenu.AppendSeparator()
        self.linkmenuitem = toolsMenu.Append(wx.ID_ANY, '&Remote Link', 'Connect to and control a remote unit')
        self.Bind(wx.EVT_MENU, self.onRemoteLink, self.linkmenuitem)
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
        
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        self.timer.Start(POLL_TIME)
        
        _icon = wx.Icon('assets/gfl_logo.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        
        self.load_bankfile(pxr.currentbank)

    def load_bankfile(self, bfile=''):
        if remote.link:
            response = remote_link_request(netlink.LOAD_BANK, bfile)
            if response == None: return
            bfile, rawbank, patches = response
            title = APP_NAME + ' - ' + bfile + '@' + remote.host
        else:
            try:
                rawbank = pxr.load_bank(bfile)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            pxr.write_config()
            patches = pxr.patch_names()
            title = APP_NAME + ' - ' + bfile
        self.currentfile = bfile
        self.btxt.Clear()
        self.btxt.AppendText(rawbank)
        self.btxt.SetInsertionPoint(0)
        self.SetTitle(title)
        self.patchlist.Clear()
        for p in patches:
            self.patchlist.Append(p)
        self.ptot = len(patches)
        self.choose_patch()

    def choose_patch(self, event=None, inc=0, pno=0):
        if event:
            n = self.patchlist.GetSelection()
            if n == wx.NOT_FOUND: return
            self.pno = n
        elif inc:
            self.pno = (self.pno + inc) % self.ptot
            self.patchlist.SetSelection(self.pno)
        else:
            self.pno = pno
            self.patchlist.SetSelection(pno)
        if remote.link:
            response = remote_link_request(netlink.SELECT_PATCH, self.pno)
            if response:
                wx.MessageBox('\n'.join(response), "Warning", wx.OK|wx.ICON_WARNING)
        else:
            warn = pxr.select_patch(self.pno)
            if warn: wx.MessageBox('\n'.join(warn), "Warning", wx.OK|wx.ICON_WARNING)

    def remote_connect(self):
        addr = wx.GetTextFromUser("Network Address (host:port):", "Remote Link", "%s:%s" % (remote.host, remote.port))
        if addr == '': return
        remote.host = addr.split(':')[0]
        if len(addr.split(':')) > 1:
            remote.port = addr.split(':')[1]
        try:
            remote.link = netlink.Client(remote.host, int(remote.port), remote.passkey)
            reply = remote.link.request(netlink.SEND_VERSION)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            remote.link = None
            return
        if not reply or reply.type != netlink.REQ_OK:
            wx.MessageBox("Unable to connect to %s" % remote.host, "Error", wx.OK|wx.ICON_ERROR)
            remote.link = None
            return
        wx.MessageBox("Connected to %s!" % remote.host, "Connected", wx.OK)
        pxr.cfg['remotelink_host'] = remote.host
        pxr.cfg['remotelink_port'] = int(remote.port)
        pxr.write_config()
        self.linkmenuitem.SetItemLabel("&Disconnect")
        pxr._fluid.router_clear()
        self.localfile = self.currentfile
        self.load_bankfile()
    
    def remote_disconnect(self):
        remote.link.close()
        remote.link = None
        self.currentfile = self.localfile
        self.load_bankfile(self.currentfile)
        self.linkmenuitem.SetItemLabel("&Remote Link")

    def onNew(self, event):
        if self.GetTitle().endswith('*'):
            resp = wx.MessageBox("Unsaved changes in bank - close anyway?", "New", wx.ICON_WARNING|wx.OK|wx.CANCEL)
            if resp != wx.OK:
                return
        self.btxt.Clear()        
        self.btxt.AppendText(" ")
        self.btxt.SetInsertionPoint(0)
        self.currentfile = ''
        if remote.link:
            self.onRefresh()
            self.SetTitle(APP_NAME + ' - (Untitled)' + '@' + remote.host)
        else:
            self.SetTitle(APP_NAME + ' - (Untitled)')

    def onOpen(self, event):
        if remote.link:
            banks = remote_link_request(netlink.LIST_BANKS)
            if banks == None: return
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
        if not self.onRefresh():
            return
        rawbank = self.btxt.GetValue()
        if remote.link:
            bfile = wx.GetTextFromUser("Bank file to save:", "Save Bank", bfile)
            if bfile == '': return
            if not bfile.endswith('.yaml'): bfile += '.yaml'
            banks = remote_link_request(netlink.LIST_BANKS)
            if banks == None: return
            if bfile in banks:
                resp = wx.MessageBox(bfile + " exists - overwrite it?", "Save", wx.ICON_WARNING|wx.OK|wx.CANCEL)
                if resp != wx.OK: return
            if remote_link_request(netlink.SAVE_BANK, patcher.write_yaml(bfile, rawbank)) == None:
                return
            self.SetTitle(APP_NAME + ' - ' + bfile + '@' + remote.host)
        else:
            if bfile == '':
                path = wx.FileSelector("Save Bank", pxr.bankdir, self.currentfile, "*.yaml", "Bank files (*.yaml)|*.yaml", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                if path == '': return
                bfile = relpath(path, start=pxr.bankdir)
            try:
                pxr.save_bank(bfile, rawbank)
            except Exception as e:
                wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                return
            pxr.write_config()
            self.SetTitle(APP_NAME + ' - ' + bfile)
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
        if remote.link:
            sfonts = remote_link_request(netlink.LIST_SOUNDFONTS)
            if sfonts == None: return
            sfont = wx.GetSingleChoice("Choose Soundfont to Open:", "Open Soundfont", sfonts)
            if sfont == '': return
        else:
            s = wx.FileSelector("Open Soundfont", pxr.sfdir, "", "*.sf2", "Soundfont (*.sf2)|*.sf2", wx.FD_OPEN)
            if s == '': return
            sfont = relpath(s, start=pxr.sfdir)
        sfbrowser = SoundfontBrowser(sfont)
        if sfbrowser.ShowModal() == wx.ID_OK:
            self.btxt.WriteText(sfbrowser.copypreset)
        sfbrowser.Destroy()
        self.choose_patch(pno=self.pno)

    def onBrowsePlugins(self, event):
        if remote.link:
            plugins = remote_link_request(netlink.LIST_PLUGINS)
            if plugins == None: return
            tmsg = TextMsgDialog(plugins, "Plugins", "Available plugins on %s:" % remote.host)
            tmsg.ShowModal()
            tmsg.Destroy()
        else:
            if not pxr.plugindir:
                pdir = wx.DirSelector("Select Plugins Directory")
                if pdir == '': return
                pxr.cfg['plugindir'] = pdir
                pxr.write_config()
            plugin = wx.FileSelector("Plugins", pxr.plugindir, "", "*.dll", "LADSPA plugin (*.dll)|*.dll")
            if plugin:
                self.btxt.WriteText(relpath(plugin, start=pxr.plugindir))

    def onListMIDI(self, event):
        if remote.link:
            response = remote_link_request(netlink.LIST_PORTS)
            if not response: return
            ports = '\n'.join(response)
            caption = "MIDI ports on %s:" % remote.host
        else:
            ports = "Inputs:\n  %s\nOutputs:\n  %s" % (
                '\n  '.join(get_input_names()),
                '\n  '.join(get_output_names()))
            caption = "Local MIDI ports:"
        tmsg = TextMsgDialog(ports, "MIDI Ports", caption)
        tmsg.ShowModal()
        tmsg.Destroy()

    def onRemoteLink(self, event=None):
        if remote.link:
            self.remote_disconnect()
        else:
            self.remote_connect()
            
    def onSettings(self, event):
        if remote.link:
            response = remote_link_request(netlink.READ_CFG)
            if not response: return
            file, rawcfg = response
        else:
            file = pxr.cfgfile
            rawcfg = pxr.read_config()
        tmsg = TextMsgDialog(rawcfg, "Settings", file, wx.OK|wx.CANCEL, edit=True, size=(500, 450))
        if tmsg.ShowModal() == wx.ID_OK:
            newcfg = tmsg.text.GetValue()
            if remote.link:
                if remote_link_request(netlink.SAVE_CFG, newcfg) == None: return
            else:
                try:
                    pxr.write_config(newcfg)
                except patcher.PatcherError as e:
                    wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
                    return
            wx.MessageBox("Configuration saved!\nRestart may be needed for some settings to apply.", "Success", wx.OK)
        tmsg.Destroy()

    def onAbout(self, event):
        msg = """
               FluidPatcher v%s
               
        Allows in-place editing and playing
           of FluidPatcher bank files.

                by Bill Peterson
                geekfunklabs.com
""" % patcher.VERSION
        msg = wx.MessageDialog(self, msg, "About", wx.OK)
        msg.ShowModal()
        msg.Destroy()

    def onRefresh(self, event=None):
        rawbank = self.btxt.GetValue()
        try:
            patcher.read_yaml(rawbank)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK|wx.ICON_ERROR)
            return False
        if remote.link:
            patches = remote_link_request(netlink.RECV_BANK, rawbank)
            if patches == None: return False
            lastpatch = self.patchlist.GetString(self.pno)
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
        
    def update(self, event):
        changed = pxr.poll_cc()
        
        
if __name__ == "__main__":
    if len(argv) > 1:
        cfgfile = argv[1]
    else:
        cfgfile = 'fluidpatcherconf.yaml'
    pxr = patcher.Patcher(cfgfile)

    host = pxr.cfg.get('remotelink_host', '127.0.0.1')
    port = pxr.cfg.get('remotelink_port', netlink.DEFAULT_PORT)    
    passkey = pxr.cfg.get('remotelink_passkey', netlink.DEFAULT_PASSKEY)
    remote = type('Remote', (object,), dict(link=None, host=host, port=port, passkey=passkey))

    app = wx.App()
    main = MainWindow()
    main.Show()
    app.MainLoop()
