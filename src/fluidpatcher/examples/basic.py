#!/usr/bin/env python3
"""
Minimal FluidPatcher example.

Loads a bank and lets you step through patches.
Play notes from any connected MIDI controller.
"""

from fluidpatcher import FluidPatcher, CONFIG

# setup
fp = FluidPatcher()

# load a bank
fp.load_bank("testbank.yaml")

print(f"Loaded bank: testbank.yaml")
print("Patches:")
for i, name in enumerate(fp.bank.patches, start=1):
    print(f"{i:>5}) {name}")
    
# select the first patch
patch_index = 0
fp.apply_patch(fp.bank.patches[patch_index])

# main loop
while True:
    print(
        f"Applied patch: {fp.bank.patches[patch_index]} "
        f"({patch_index + 1}/{len(fp.bank.patches)})"
    )

    cmd = input("Enter = next patch | q = quit: ").lower()

    if cmd == "q":
        break
    else:
        patch_index = (patch_index + 1) % len(fp.bank.patches)
        patch_name = fp.bank.patches[patch_index]
        fp.apply_patch(patch_name)

