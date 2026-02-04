#!/usr/bin/env python3
"""
Live YAML editor for fluidpatcher banks.

Edits in the text pane are parsed immediately. Discovered patches
are added to the Patch menu, and can be applied to audition changes
to the bank. Bank errors are shown in the status bar and dumped to
stdout while editing - this is diagnostic and non-breaking.

Note: this editor can be used alongside a DAW.
Connect MIDI/audio to fluidsynth.
"""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
import traceback

from yaml import YAMLError

import fluidpatcher
from fluidpatcher.bankfiles import BankSyntaxError, BankValidationError

BANKS_PATH = fluidpatcher.CONFIG["banks_path"]

class BankEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FluidPatcher Live Bank Editor")
        self.geometry("900x600")
        self.lastfile = ""
        self._parse_after_id = None

        # create menus
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=False)
        filemenu.add_command(
            label="Open", underline=0, command=self.open_file
        )
        filemenu.add_command(
            label="Save", underline=0, command=self.save_file
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Quit", underline=0, command=self.quit
        )
        self.patchmenu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(
            label="File", menu=filemenu, underline=0
        )
        menubar.add_cascade(
            label="Patches", menu=self.patchmenu, underline=0
        )
        self.config(menu=menubar)

        # create widgets
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text = tk.Text(
            self,
            wrap="none",
            undo=True,
            font="TkFixedFont",
        )
        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.text.configure(yscrollcommand=yscroll.set,
                            xscrollcommand=xscroll.set)
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.columnconfigure(0, weight=1)
        self.status_left = ttk.Label(bar, text="Ready", anchor="w")
        self.status_right = ttk.Label(bar, text="Ln 1, Col 1", anchor="e")
        self.status_left.grid(row=0, column=0, sticky="ew", padx=4)
        self.status_right.grid(row=0, column=1, sticky="e", padx=4)

        # add binds
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<KeyRelease>", self._update_cursor_pos)
        self.text.bind("<ButtonRelease>", self._update_cursor_pos)

    def open_file(self):
        f = filedialog.askopenfilename(
            initialdir=self.lastfile.parent if self.lastfile else BANKS_PATH,
            initialfile=self.lastfile.name if self.lastfile else "",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not f:
            return
        self.lastfile = Path(f)
        content = self.lastfile.read_text()
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._update_cursor_pos()

    def save_file(self):
        f = filedialog.asksaveasfilename(
            initialdir=self.lastfile.parent if self.lastfile else BANKS_PATH,
            initialfile=self.lastfile.name if self.lastfile else "",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if not f:
            return
        self.lastfile = Path(f)
        self.lastfile.write_text(self.text.get("1.0", "end-1c"))
        self.set_status(f"Saved {f}")

    def _on_text_modified(self, e=None):
        self.text.edit_modified(False)
        if self._parse_after_id is not None:
            self.after_cancel(self._parse_after_id)
        self._parse_after_id = self.after(300, self.parse_bank)

    def _update_cursor_pos(self, e=None):
        line, col = self.text.index("insert").split(".")
        self.status_right.config(text=f"Ln {line}, Col {int(col) + 1}")

    def parse_bank(self):
        self._parse_after_id = None
        text = self.text.get("1.0", "end-1c")
        try:
            fp.load_bank(raw=text)
        except Exception as e:
            if isinstance(e, BankSyntaxError) and e.mark:
                buflines = e.mark.buffer.splitlines()
                for i, line in enumerate(text.splitlines()):
                    if line in buflines:
                        if buflines.index(line) == e.mark.line:
                            break
                        if buflines.index(line) > e.mark.line:
                            i -= 1
                            break
                self.set_status(f"{type(e).__name__}: {e.msg} on line {i + 1}")
            else:
                self.set_status(f"{type(e).__name__}: {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
            self.status_left.configure(foreground="red")
        else:
            self.status_left.configure(foreground="black")
            self.patchmenu.delete(0, self.patchmenu.index('end'))
            for i, name in enumerate(fp.bank.patches):
                self.patchmenu.add_command(
                    label=name,
                    command=lambda n=name: self.select_patch(n)
                )
            self.set_status("Bank parsed successfully")

    def select_patch(self, name):
        fp.apply_patch(name)
        self.set_status(f"Applied patch {name}")

    def set_status(self, msg: str):
        self.status_left.config(text=msg.replace("\n", " "))

fp = fluidpatcher.FluidPatcher()

def main():
    app = BankEditorApp()
    app.mainloop()

if __name__ == "__main__":
    main()


