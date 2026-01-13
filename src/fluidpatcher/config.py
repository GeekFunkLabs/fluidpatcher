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


def load_config():
    """
    Load configuration from disk and finalize derived paths.

    Returns
    -------
    dict
        A configuration mapping loaded from CONFIG_PATH (YAML), with:
        - any *_path entries converted to pathlib.Path
        - default fallback paths for banks, sounds, and midi if missing
        - ladspa_path resolved from environment or system default

    The returned mapping does NOT modify the global CONFIG object; the
    module updates CONFIG separately after import.
    """
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    for key, val in list(cfg.items()):
        if key.endswith("_path") and val is not None:
            cfg[key] = Path(val)
    cfg.setdefault("banks_path", CONFIG_PATH.parent / "banks")
    cfg.setdefault("sounds_path", cfg["banks_path"].parent / "sounds")
    cfg.setdefault("midi_path", cfg["banks_path"].parent / "midi")
    cfg.setdefault(
        "ladspa_path",
        Path(os.getenv("LADSPA_PATH", "/usr/lib/ladspa"))
    )
    return cfg


def save_config():
    """
    Persist the current CONFIG mapping back to CONFIG_PATH.

    Converts Path values to POSIX strings for YAML serialization and
    writes the result to disk without reordering keys. Raises if the
    file cannot be written.
    """
    cfg_posix = {
        k: v.as_posix() if isinstance(v, Path) else v
        for k, v in CONFIG.items()
    }
    CONFIG_PATH.write_text(
        yaml.safe_dump(cfg_posix, sort_keys=False)
    )


CONFIG_PATH = Path(os.getenv(
    "FLUIDPATCHER_CONFIG",
    "~/.config/fluidpatcher/fluidpatcherconf.yaml"
)).expanduser()

if not CONFIG_PATH.exists():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(res.files("fluidpatcher.data") / "fluidpatcherconf.yaml", CONFIG_PATH)

CONFIG = load_config()
if not CONFIG["banks_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "banks", CONFIG["banks_path"])
if not CONFIG["sounds_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "sounds", CONFIG["sounds_path"])
if not CONFIG["midi_path"].exists():
    shutil.copytree(res.files("fluidpatcher.data") / "midi", CONFIG["midi_path"])

patchcord = res.files("fluidpatcher._ladspa") / "patchcord.so" 
arch = platform.machine()
prebuilt_path = res.files("fluidpatcher._ladspa") / f"prebuilt/linux-{arch}/patchcord.so"

if patchcord.exists():
    PATCHCORD = patchcord
elif prebuilt_path.exists():
    PATCHCORD = prebuilt_path
else:
    PATCHCORD = None

