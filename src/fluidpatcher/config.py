"""
Configuration loading and initialization for fluidpatcher.

This module defines where fluidpatcher stores its configuration data
(~/.config/fluidpatcher/... by default), loads settings on import,
creates missing directories, and populates them with bundled defaults
when needed.

At runtime:
- CONFIG holds the merged configuration mapping
- CONFIG_PATH stores the config file path
- PATCHCORD resolves to a LADSPA plugin .so suitable for this machine,
  or None if no build is available
"""
import importlib.resources as res
import os
from pathlib import Path
import platform
import shutil

import yaml

from .bankfiles import LadspaEffect


DEFAULT_CFG = """\
fluidsettings:
  midi.autoconnect: 1
  player.reset-synth: 0
  synth.ladspa.active: 1
  synth.audio-groups: 16
"""

CONFIG_PATH = Path(os.getenv(
    "FLUIDPATCHER_CONFIG",
    "~/.config/fluidpatcher/fluidpatcherconf.yaml"
)).expanduser()

# load configuration
CONFIG = yaml.safe_load(DEFAULT_CFG)
if not CONFIG_PATH.exists():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(DEFAULT_CFG)
else:
    CONFIG |= yaml.safe_load(CONFIG_PATH.read_text())

# parse config
for key, val in list(CONFIG.items()):
    if key.endswith("_path") and val is not None:
        CONFIG[key] = Path(val)
CONFIG.setdefault(
    "ladspa_path",
    Path(os.getenv("LADSPA_PATH", "/usr/lib/ladspa"))
)

# create default files as needed
localshare = Path.home() / ".local/share/fluidpatcher"
for item in "banks", "sounds", "midi":
    key = item + "_path"
    CONFIG.setdefault(key, localshare / item)
    if not CONFIG[key].exists():
        shutil.copytree(res.files("fluidpatcher.data") / item, CONFIG[key])

# initialize patchcord for multi-channel LADSPA mixing
system = platform.system().lower()
arch = platform.machine()
prebuilt_path = res.files("fluidpatcher._ladspa") / f"prebuilt/{system}-{arch}/patchcord.so"
patchcord = res.files("fluidpatcher._ladspa") / "patchcord.so"

if patchcord.exists():
    PATCHCORD = {"_patchcord": LadspaEffect(lib=patchcord)}
elif prebuilt_path.exists():
    PATCHCORD = {"_patchcord": LadspaEffect(lib=prebuilt_path)}
else:
    PATCHCORD = {}
    CONFIG["fluidsettings"]["synth.audio-groups"] = 1

