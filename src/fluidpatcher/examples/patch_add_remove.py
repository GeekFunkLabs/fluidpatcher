#!/usr/bin/env python3
"""
Adding and removing patches at runtime

Normally banks are created and loaded as YAML. This example shows how
to modify a bank within a program.
"""

from fluidpatcher import FluidPatcher, CONFIG, SFPreset, MidiRule

# the MIDI channel of notes from your controller
MIDI_CHANNEL = 1

# setup, suppress fluidsynth logging
fp = FluidPatcher(fluidlog=-1)

# load a soundfont
soundfont = fp.load_soundfont(CONFIG["sounds_path"] / "test.sf2")
print(f"Loaded soundfont: {soundfont.file}")

# create a patch
fp.bank.patch["Piano"] = {
    MIDI_CHANNEL: SFPreset(soundfont.file, 0, 4)
}

# set a rule at the root level so notes go to the synth
fp.bank.root["rules"] = [
    MidiRule(type="note", chan=MIDI_CHANNEL)
]

patch_name = ""
# main loop
while True:
    print("Patches:")
    for i, name in enumerate(fp.bank.patches, start=1):
        print(">" if name == patch_name else " ", end="")
        print(f"{i:>5}) {name}")

    cmd = input(
        "# = select patch | a = add patch | d = delete patch | q = quit: "
    ).lower()

    if cmd.isdigit():
        if 0 < int(cmd) <= len(fp.bank.patches):
            patch_name = fp.bank.patches[int(cmd) - 1]
            fp.apply_patch(patch_name)
        else:
            print("Patch number out of range")

    elif cmd == "a":
        name = input("Enter new patch name: ")
        if name == "":
            continue
        elif name in fp.bank.patches:
            print(f"Patch {name} already exists")
            continue

        print("preset bank:prog name")
        print("====== ========= ====")
        for i, (bank, prog) in enumerate(soundfont, start=1):
            print(f"{i:>6}  {bank:03}:{prog:03}  {soundfont[bank, prog]}")

        p = input("Enter preset #: ")
        if p.isdigit():
            i = int(p) - 1
            if 0 <= i < len(soundfont):
                bank, prog = list(soundfont)[i]
                fp.bank.patch[name] = {
                    MIDI_CHANNEL: SFPreset(soundfont.file, bank, prog)
                }
            else:
                print("Preset number out of range")

    elif cmd == "d":
        name = input("Enter name of patch delete: ")
        if name in fp.bank.patches:
            del fp.bank.patch[name]
        else:
            print(f"Patch name '{name}' not found")

    elif cmd == "q":
        break

