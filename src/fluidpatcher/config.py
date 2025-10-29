import importlib.resources as res
import os
from pathlib import Path
import platform
import shutil

import yaml


def load_config():
    CONFIG = yaml.safe_load(CONFIG_PATH.read_text())
    CONFIG["banks_path"] = Path(
        CONFIG.get("banks_path", CONFIG_PATH.parent / "banks")
    )
    CONFIG["sounds_path"] = Path(
        CONFIG.get("sounds_path", CONFIG["banks_path"].parent / "sounds")
    )
    CONFIG["midi_path"] = Path(
        CONFIG.get("midi_path", CONFIG["banks_path"].parent / "midi")
    )
    CONFIG["ladspa_path"] = Path(
        CONFIG.get("ladspa_path", Path(os.getenv("LADSPA_PATH"))
    )
    return CONFIG


def save_state(config):
    config_posix = {k: v.as_posix() if isinstance(v, Path) else v
                    for k, v in config.items()}
    CONFIG_PATH.write_text(yaml.safe_dump(config_posix, sort_keys=False))


CONFIG_PATH = Path(os.getenv(
    "FLUIDPATCHER_CONFIG",
    "~/.config/fluidpatcher/fluidpatcherconf.yaml"
)).expanduser()

if not CONFIG_PATH.exists():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(res.files("fluidpatcher.data") / "fluidpatcherconf.yaml", CONFIG_PATH)

CONFIG = load_config()

patchcord = res.files("fluidpatcher._ladspa") / "patchcord.so" 
arch = platform.machine()
prebuilt_path = res.files("fluidpatcher._ladspa") / f"prebuilt/linux-{arch}/patchcord.so"

if patchcord.exists():
    PATCHCORD = patchcord
elif prebuilt_path.exists():
    PATCHCORD = prebuilt_path
else:
    PATCHCORD = None

