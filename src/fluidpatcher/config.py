import importlib.resources as res
import os
from pathlib import Path
import shutil

import yaml


CONFIG_PATH = Path(os.getenv(
    "FLUIDPATCHER_CONFIG",
    "~/.config/fluidpatcher/fluidpatcherconf.yaml"
)).expanduser()

LADSPA_PATH = Path(os.getenv("LADSPA_PATH"))

if not CONFIG_PATH.exists():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(res.files("fluidpatcher.data") / "fluidpatcherconf.yaml", CONFIG_PATH)

def load_config():
    CONFIG = yaml.safe_load(CONFIG_PATH.read_text())
    CONFIG.setdefault("banks_path", CONFIG_PATH.parent / "banks")
    CONFIG.setdefault("sounds_path", CONFIG["banks_path"].parent / "sounds")
    CONFIG.setdefault("midi_path", CONFIG["banks_path"].parent / "midi")
    if LADSPA_PATH:
        CONFIG.setdefault("ladspa_path", LADSPA_PATH)
    return CONFIG

def save_state(config):
    CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))

CONFIG = load_config()

