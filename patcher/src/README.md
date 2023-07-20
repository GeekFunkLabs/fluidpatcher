# sbmidi

A shared object library with functions for creating a duplex ALSA driver and an advanced midi router, targeted specifically at the squishbox

To build (on linux (raspberry pi)):
```
gcc -shared -o libsbmidi.so `pkg-config --cflags glib-2.0` sbmidi_alsa.c sbmidi_router.c sbmidi_event.c `pkg-config --libs glib-2.0 alsa`
```
