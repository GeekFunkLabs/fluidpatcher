import importlib.resources as res
import os
from pathlib import Path
import platform
import shutil

import yaml


def load_config():
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    cfg["banks_path"] = Path(
        cfg.get("banks_path", CONFIG_PATH.parent / "banks")
    )
    cfg["sounds_path"] = Path(
        cfg.get("sounds_path", cfg["banks_path"].parent / "sounds")
    )
    cfg["midi_path"] = Path(
        cfg.get("midi_path", cfg["banks_path"].parent / "midi")
    )
    cfg["ladspa_path"] = Path(
        cfg.get("ladspa_path", Path(
            os.getenv("LADSPA_PATH", "/usr/lib/ladspa"))
        )
    )
    if "current_bank" in cfg:
        cfg["current_bank"] = Path(cfg["current_bank"])
    return cfg


def save_state(cfg):
    cfg_posix = {k: v.as_posix() if isinstance(v, Path) else v
                 for k, v in cfg.items()}
    CONFIG_PATH.write_text(yaml.safe_dump(cfg_posix, sort_keys=False))


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

