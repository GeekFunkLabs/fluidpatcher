# Overview

FluidPatcher is a lightweight, configuration-driven tool for building
Python programs that control FluidSynth. Rather than embedding
synthesizer logic directly in code, FluidPatcher relies on descriptive,
YAML-based **bank files**. A bank file defines what the synthesizer
*does*: playing notes, routing MIDI, triggering sequences, enabling
effects, and so on. Put simply: the musical behavior lives in the bank,
while Python provides the front-end that loads, manages, and switches
between those definitions.

Using FluidPatcher, a Python application takes care of tasks like
loading and saving banks, activating patches, and loading/unloading
soundfonts as needed. Because the musical configuration is
externalized, users can create complex performance setups without
modifying Python code. Bank files may be tailored to specific sets,
rehearsals, or genres, making them easy to reuse, adapt, and share
between systems.

The module `pfluidsynth.py` communicates with the FluidSynth library
through `ctypes`, but this interaction is not exposed directly. Instead,
the module wraps FluidSynth’s API inside higher-level classes such as
`Sequence`, `LadspaEffect`, and others. When a bank file is parsed,
FluidPatcher constructs corresponding Python objects to represent the
instruments, routers, effects, and players declared in the file. These
objects can be manipulated at runtime and re-applied, enabling dynamic
reconfiguration during a session.

This section introduces the core concepts and components of
FluidPatcher: what kinds of objects exist, how they are expressed in
YAML, how they fit together, and what role they play in a typical
workflow. Bank files can be as simple or as elaborate as needed.
Many ideas are best learned through worked examples, so the Tutorials
expand on these concepts using live demonstrations, and the Cookbook
highlights useful patterns that can be copied into new banks.

Questions, examples, and discussion are welcome on the project’s GitHub
Discussions page.

