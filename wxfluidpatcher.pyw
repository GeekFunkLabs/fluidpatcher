#!/usr/bin/env python

import os, sys, wx
from subprocess import call, check_output
import patcher

##### User-configurable stuff
DEFAULT_WIDTH  = 700        # app default width
DEFAULT_HEIGHT = 600        # app default height
APP_NAME = 'FluidPatcher'

class SoundfontBrowser(wx.Dialog):
    def __init__(self, sf):
        super(SoundfontBrowser, self).__init__(None, size=(400,650), title=sf,
                                                style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.sf = sf
        self.copypreset = ''

        self.presetlist = wx.ListCtrl(self, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.presetlist.AppendColumn('Bank')
        self.presetlist.AppendColumn('Preset')
        self.presetlist.AppendColumn('Name')

        pxr.load_soundfont(sf)
        for item in [["%03d:" % bank, "%03d:" % prog, name] for name, bank, prog in pxr.sfpresets]:
            self.presetlist.Append(item)
        
        self.presetlist.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.presetlist.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.presetlist.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.preset_select, self.presetlist)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onActivate, self.presetlist)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        self.preset_select(val=0)
        
    def preset_select(self, event=None, val=''):
        if val == 0:
            self.pno = 0
            self.presetlist.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            return
        elif val == 1 or val == -1:
            self.pno = (self.pno + val) % len(pxr.bank['patches'])
            self.presetlist.SetItemState(self.pno, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            return
        else:
            self.pno = self.presetlist.GetNextSelected(-1)
            if self.pno < 0: return
        pxr.select_sfpreset(self.pno)

    def onKeyPress(self, event):
        if event.GetModifiers()<=0:
            if event.GetKeyCode() == wx.WXK_ESCAPE:
                self.EndModal(wx.CANCEL)
                return
        event.Skip()
        
    def onActivate(self, event):
        bank, prog = pxr.sfpresets[event.GetIndex()][1:3]
        self.copypreset = "%s:%03d:%03d" % (self.sf, bank, prog)
        self.EndModal(wx.ID_OK)

class MainWindow(wx.Frame):
    def __init__(self):
        super(MainWindow, self).__init__(None, size=(700,600), title=APP_NAME)
                
### Create Menus
        fileMenu = wx.Menu()
        
        item = fileMenu.Append(wx.ID_OPEN, 'L&oad Bank...\tCtrl+O', 'Load bank file')
        item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
        self.Bind(wx.EVT_MENU, self.onOpen, item)
        
        item = fileMenu.Append(wx.ID_SAVEAS, '&Save Bank\tCtrl+S', 'Save current bank')
        item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE))
        self.Bind(wx.EVT_MENU, self.onSave, item)
        
        item = fileMenu.Append(wx.ID_SAVEAS, 'Save Bank &As...\tCtrl+Shift+S', 'Save bank file')
        item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE_AS))
        self.Bind(wx.EVT_MENU, self.onSaveAs, item)
        
        item = fileMenu.Append(wx.ID_ANY, 'Browse Sound&Font...', 'Open a soundfont and browse presets')
        self.Bind(wx.EVT_MENU, self.onOpenSoundfont, item)
        fileMenu.AppendSeparator()
        item = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q', 'Terminate the program')
        item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_QUIT))
        self.Bind(wx.EVT_MENU, self.onExit, item)

        helpMenu = wx.Menu()
        item = helpMenu.Append(wx.ID_ABOUT, '&About', 'Information about this program')
        item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(16,16)))
        self.Bind(wx.EVT_MENU, self.onAbout, item)

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, '&File')
        menuBar.Append(helpMenu, '&Help')
        self.SetMenuBar(menuBar)

### Toolbar
        patchTool = self.CreateToolBar()
        tool = patchTool.AddTool(wx.ID_REFRESH, 'Prev', wx.ArtProvider.GetBitmap(wx.ART_REDO), 'Refresh patches (F5)')
        tool.SetLongHelp('Refresh patches from editor text')
        self.Bind(wx.EVT_TOOL, self.onRefresh, tool)
        tool = patchTool.AddTool(wx.ID_ANY, 'Prev', wx.ArtProvider.GetBitmap(wx.ART_MINUS), 'Select previous patch (F7)')
        tool.SetLongHelp('Select previous patch')
        self.Bind(wx.EVT_TOOL, lambda x: self.patch_select(x, -1), tool)
        tool = patchTool.AddTool(wx.ID_ANY, 'Next', wx.ArtProvider.GetBitmap(wx.ART_PLUS), 'Select next patch (F8)')
        tool.SetLongHelp('Select next patch')
        self.Bind(wx.EVT_TOOL, lambda x: self.patch_select(x, 1), tool)
        self.patchlist = wx.Choice(patchTool)
        tool = patchTool.AddControl(self.patchlist, 'Patches')
        self.Bind(wx.EVT_CHOICE, self.patch_select, self.patchlist)

        patchTool.Realize()        

### create window elements
        self.btxt = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_RICH|
                                            wx.TE_NOHIDESEL|wx.HSCROLL)
        fwf = wx.Font(wx.FontInfo().Family(wx.FONTFAMILY_TELETYPE))
        self.btxt.SetDefaultStyle(wx.TextAttr(wx.NullColour, font=fwf))
        self.CreateStatusBar()

        self.Bind(wx.EVT_CLOSE, self.onExit)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        _icon = wx.Icon('images/gfl_logo.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        self.SetSize(size=wx.Size(DEFAULT_WIDTH, DEFAULT_HEIGHT))

        self.load_bankfile(pxr.cfg['currentbank'])

    def load_bankfile(self, file):
        try:
            pxr.load_bank(file)
        except Exception as e:
            self.SetStatusText(str(e).replace('\n', ' '))
            return
        self.SetTitle(APP_NAME + ' - ' + pxr.cfg['currentbank'])
        f = open(os.path.join(pxr.bankdir, pxr.cfg['currentbank']))
        rawbank = f.read()
        f.close()
        self.btxt.Clear()
        self.btxt.AppendText(rawbank)
        self.btxt.SetInsertionPoint(0)
        for p in pxr.bank['patches']:
            self.patchlist.Append(p)
        self.patch_select(val=0)
            
    def patch_select(self, event=None, val=''):
        if val == 0:
            self.pno = 0
            self.patchlist.SetSelection(0)
        elif val == 1 or val == -1:
            self.pno = (self.pno + val) % len(pxr.bank['patches'])
            self.patchlist.SetSelection(self.pno)
        else:
            n = self.patchlist.GetSelection()
            if n == wx.NOT_FOUND: return
            self.pno = n
        warn = pxr.select_patch(self.pno)
        if warn:
            self.SetStatusText(warn)
        
    def onOpen(self, event):
        dialog = wx.FileDialog(None, "Load Bank", pxr.bankdir,
                                wildcard="Bank files (*.yaml,*.yml)|*.yaml;*.yml",
                                style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            bfile = os.path.relpath(dialog.GetPath(), start=pxr.bankdir)
            dialog.Destroy()
            self.load_bankfile(bfile)
        else:
            dialog.Destroy()
        
    def onSave(self, event):
        self.onSaveAs(bfile=pxr.cfg['currentbank'])
        
    def onSaveAs(self, event=None, bfile=''):
        rawbank = self.btxt.GetValue()
        try:
            patcher.read_yaml(rawbank)
        except Exception as e:
            self.SetStatusText(str(e).replace('\n', ' '))
            return
        if bfile == '':
            dialog = wx.FileDialog(None, "Save Bank", pxr.bankdir, pxr.cfg['currentbank'],
                wildcard="Bank files (*.yaml,*.yml)|*.yaml;*.yml", style=wx.FD_SAVE)
            if dialog.ShowModal() == wx.ID_OK:
                bfile = os.path.relpath(dialog.GetPath(), start=pxr.bankdir)
                dialog.Destroy()
            else:
                dialog.Destroy()
                return
        try:
            pxr.save_bank(bfile, rawbank)
        except Exception as e:
            self.SetStatusText(str(e).replace('\n', ' '))
        self.SetStatusText('Saved ' + bfile)
        self.SetTitle(APP_NAME + ' - ' + pxr.cfg['currentbank'])
                
    def onOpenSoundfont(self, event):
        dialog = wx.FileDialog(None, "Open Soundfont", pxr.sfdir,
            wildcard="Soundfont (*.sf2)|*.sf2", style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            sfont = os.path.relpath(dialog.GetPath(), start=pxr.sfdir)
            dialog.Destroy()
            sfbrowser = SoundfontBrowser(sfont)
            if sfbrowser.ShowModal() == wx.ID_OK:
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(sfbrowser.copypreset))
                    wx.TheClipboard.Close()
                    dlg = wx.MessageDialog(self, "Preset copied to clipboard!", "Preset", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
            sfbrowser.Destroy()
            self.onRefresh()
        else:
            dialog.Destroy()
            return

    def onExit(self, event):
        self.Destroy()
        
    def onAbout(self, event):
        msg = """
               Fluid Patcher v0.1
               
        Allows in-place editing and playing
           of FluidPatcher bank files.

                by Bill Peterson
                geekfunklabs.com
"""
        dlg = wx.MessageDialog(self, msg, "About", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def onRefresh(self, event=None):
        rawbank = self.btxt.GetValue()
        try:
            pxr.load_bank(rawbank)
        except Exception as e:
            self.SetStatusText(str(e).replace('\n', ' '))
            return
        self.btxt.Clear()
        self.btxt.AppendText(rawbank)
        self.btxt.SetInsertionPoint(0)
        for p in pxr.bank['patches']:
            self.patchlist.Append(p)
        self.patch_select(val=0)
        self.SetTitle(APP_NAME)
        
    def onKeyPress(self, event):
        if event.GetModifiers()<=0:
            if event.GetKeyCode() == wx.WXK_F5:
                self.onRefresh()
                return
            if event.GetKeyCode() == wx.WXK_F7:
                self.patch_select(val=-1)
                return
            if event.GetKeyCode() == wx.WXK_F8:
                self.patch_select(val=1)
                return
        event.Skip()
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cfgfile = sys.argv[1]
    else:
        cfgfile = 'patcherconf.yaml'
    pxr = patcher.Patcher(cfgfile)

    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.MainLoop()
