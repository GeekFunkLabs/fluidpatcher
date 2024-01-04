[LADSPA](https://www.ladspa.org/) plugins are optional separate programs that provide additional audio effects. They can be used on many platforms, but at this time support is only provided for Linux setup. To install a base LADSPA system and several batches of plugins, enter

```bash
sudo apt-get install ladspa-sdk swh-plugins tap-plugins wah-plugins
```

To compile and install `patchcord.so`, which is used for chaining plugins, go to the `src/` folder and enter

```bash
sudo gcc -shared patchcord.c -o /usr/lib/ladspa/patchcord.so
```
