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


def save_config():
    """
    Writes CONFIG to file.
    """
    if not CONFIG_PATH.parent.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg_posix = {
        k: v.as_posix() if isinstance(v, Path) else v
        for k, v in CONFIG.items()
    }
    CONFIG_PATH.write_text(
        yaml.safe_dump(cfg_posix, sort_keys=False)
    )


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
if CONFIG_PATH.exists:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    CONFIG.update(cfg)

for key, val in list(CONFIG.items()):
    if key.endswith("_path") and val is not None:
        CONFIG[key] = Path(val)
CONFIG.setdefault("banks_path", CONFIG_PATH.parent / "banks")
CONFIG.setdefault("sounds_path", CONFIG["banks_path"].parent / "sounds")
CONFIG.setdefault("midi_path", CONFIG["banks_path"].parent / "midi")
CONFIG.setdefault(
    "ladspa_path",
    Path(os.getenv("LADSPA_PATH", "/usr/lib/ladspa"))
)

# create default files as needed
if not CONFIG_PATH.exists():
    save_config()
if not CONFIG["banks_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "banks", CONFIG["banks_path"])
if not CONFIG["sounds_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "sounds", CONFIG["sounds_path"])
if not CONFIG["midi_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "midi", CONFIG["midi_path"])

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

