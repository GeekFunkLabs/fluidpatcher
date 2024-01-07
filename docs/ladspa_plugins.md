# Plugins

[LADSPA](https://www.ladspa.org/) plugins are optional separate programs that provide additional audio effects. It is possible to compile and use them on other platforms, but at this time support is only provided for Linux usage.

## Setup

To install a base LADSPA system and several batches of plugins, enter

```bash
sudo apt-get install ladspa-sdk swh-plugins tap-plugins wah-plugins
```

To compile and install `patchcord.so`, which is used for mixing channels to outputs, go to the `src/` folder and enter

```bash
sudo gcc -shared patchcord.c -o /usr/lib/ladspa/patchcord.so
```

## Usage

* where are they, config file settings (plugindir, synth.ladspa.active, synth.audio.groups)
* audio groups - what are they, how mixing works
* analyseplugin - get audio, control port names
