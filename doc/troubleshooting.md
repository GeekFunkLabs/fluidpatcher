# Troubleshooting


This document will help you to diagnose and deal with issues when running the _headlesspi.py_ and _squishbox.py_ scripts. These scripts are designed to be run on a Raspberry Pi without a monitor or keyboard attached, so they don't have ways to give you lots of information when an error occurs.

- [First Steps](#first-steps-getting-information) below will help you figure out what might be causing your problem
- [Common Issues](#common-issues) are listed further down.

Feel free to ask for more help by posting an [issue](https://github.com/albedozero/fluidpatcher/issues) or emailing white2rnado@geekfunklabs.com.


## First Steps: Getting Information

### View Program Errors

If you're having problems, it can help to see the full error output. To do this, you need to [log in to the Raspberry Pi remotely](https://www.raspberrypi.com/documentation/computers/remote-access.html) or plug in a monitor and keyboard so you can interact with it directly. You will then run the script from a command line to see what the error is.

To disable the service that runs the _headlesspi.py_ or _squishbox.py_ script in the background, enter

```bash
sudo systemctl stop squishbox.service
```

Then, to run the script directly, enter `./headlesspi.py` or `./squishbox.py`. The script will now run as it does on startup, but any errors will now be printed to the screen with a lot of additional information. You can press Control-C to quit the program at any time.

### List Connected Devices

If your MIDI controllers or sound output are not working, it can be useful to see if they're actually being detected. To list connected MIDI devices, enter the command
```bash
aconnect -i
```
You will see output similar to this:
```
client 0: 'System' [type=kernel]
    0 'Timer           '
    1 'Announce        '
client 14: 'Midi Through' [type=kernel]
    0 'Midi Through Port-0'
client 24: 'AKM322' [type=kernel,card=2]
    0 'AKM322 MIDI 1   '
```
To list detected audio devices, enter
```bash
aplay -l
```
You will see output similar to that below. The name after each card number is a unique identifier for the device.
```
**** List of PLAYBACK Hardware Devices ****
card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
  Subdevices: 8/8
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
  Subdevice #7: subdevice #7
card 1: sndrpihifiberry [snd_rpi_hifiberry_dac], device 0: HifiBerry DAC HiFi pcm5102a-hifi-0 [HifiBerry DAC HiFi pcm5102a-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 3: vc4hdmi [vc4-hdmi], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

### Monitor MIDI Messages

Sometimes, it is also useful to see what MIDI messages your controller is actually sending. Find your MIDI controller's port number using the `aconnect -i` command as above and use it in the command below.
```bash
aseqdump -p 24
```
Manipulating the keys/pads/knobs/etc. on your controller will cause MIDI messages to be output to the screen, such as those shown below.
```
Waiting for data. Press Ctrl+C to end.
Source  Event                  Ch  Data
 24:0   Control change          0, controller 21, value 127
 24:0   Control change          0, controller 21, value 0
 24:0   Control change          0, controller 22, value 127
 24:0   Control change          0, controller 22, value 0
 24:0   Control change          0, controller 24, value 127
 24:0   Control change          0, controller 24, value 0
 24:0   Note on                 0, note 48, velocity 127
 24:0   Note off                0, note 48, velocity 0
 24:0   Note on                 0, note 50, velocity 102
 24:0   Note off                0, note 50, velocity 0
```


## Common Issues

- [I don't hear any sound.](#i-dont-hear-any-sound)

- [The audio crackles/stutters or there's too much latency.](#the-audio-cracklesstutters-or-theres-too-much-latency)

- [I can play notes, but I can't switch patches using the buttons on my controller.](#i-can-play-notes-but-i-cant-switch-patches-using-the-buttons-on-my-controller)

- [When I switch patches using the buttons on my controller, the Pi shuts down.](#when-i-switch-patches-using-the-buttons-on-my-controller-the-pi-shuts-down)

- [The Pi displays an error or crashes/reboots.](#the-pi-displays-an-error-or-crashesreboots)

### I don't hear any sound.

If you have checked the typical things, such as turning up the volume using the `alsamixer` program and making sure your headphones/connecting wires actually work and are plugged in all the way, it may be that you need to select the correct audio output device. Audio device selection should be handled by the [install script](README.md#raspberry-pi), which can be run again to change these settings, but you can manually set the audio device as well. How this is done depends on the audio driver you are using, which is chosen by the `audio.driver` fluidsetting in your [config file](patcher/file_formats.md).

Find the name of your audio device using the `aplay -l` command as described [above](#list-connected-devices). When setting the device, it should be preceded by the interface type, which can be `hw:` or `plughw:` - in most cases `hw:` works, but if you encounter problems `plughw:` may help. If you are using the `alsa` audio driver, set your audio device using the `audio.alsa.device` fluidsetting. The settings for the `jack` audio driver are determined by the command line stored in the _$HOME/.jackdrc_ file, which is used to start the JACK server. A typical example is shown below - edit the file and change the value of `--device` to choose your audio device.
```bash
/usr/bin/jackd --silent --realtime -d alsa --softmode --playback -S \
--device hw:sndrpihifiberry --period 64 --nperiods 3 --rate 44100
```

### The audio crackles/stutters or there's too much latency.

Stutters (gaps in the audio) are caused by not having enough audio buffer space for the processor to use in between writing to the sound output, while audio latency (the delay between playing a note and hearing it) increases with the amount of buffer space the processor has to fill. The amount of buffer space depends on the settings of your audio driver. The default audio driver and buffer settings should be optimal for the Raspberry Pi, but you can try adjusting them if you have issues.

The audio driver used is set by the `audio.driver` fluidsetting in your [config file](patcher/file_formats.md). For the `alsa` audio driver, the number of audio buffers and their size are determined by the `audio.periods` and `audio.period-size` fluidsettings. To change the settings for the `jack` driver modify the `--period` and `--nperiods` values in the _$HOME/.jackdrc_ file as described [above](#i-dont-hear-any-sound).

You may also hear audio crackling if the synth is too loud, overloading the audio output. Turn the volume down or adjust the `synth.gain` fluidsetting to compensate.

### I can play notes, but I can't switch patches using the buttons on my controller.

The channel and controller numbers sent by the pads/knobs/sliders/etc. on your controller that you want to use to change patches must match the values set at the top of the [_headlesspi.py_](headlesspi.py) script. [Confirm](#monitor-midi-messages) what messages your controller is actually sending. You can either edit the script and change the values to the ones your controller sends, or reprogram your controller using its included software or the method described in its user manual.

### When I switch patches using the buttons on my controller, the Pi shuts down.

The buttons/pads on your controller should be programmed to send _momentary_ control change (CC) values. This means the controller sends a nonzero value when you press it, and a zero value when you release. Buttons/pads on a controller can usually be set to either _momentary_ or _toggle_ behavior. In the latter case the pad sends a nonzero value on the first press, nothing when released, and a zero value only when it is pressed a second time. Until the second press, the program is fooled into thinking you are holding the button down, which is the signal to shut down the Pi. Some controllers have buttons that never send a zero CC value at all, causing the same issue.

You can reprogram your controller to send the appropriate momentary messages or change the values at the top of the [_headlesspi.py_](headlesspi.py) script. You can also set `SHUTDOWN_BTN` to be something other than the patch change buttons. One could also modify the `connect_controls()` function to use note messages instead of control changes.

### The Pi displays an error or crashes/reboots.

The _squishbox.py_ script will give information about the error on the LCD, and _headlesspi.py_ will blink one of its LEDs in a [repeating pattern](programs.md#headlesspipy). The software will try to recover from the error, but it may cause the Pi to ignore some/all input, restart, or hang. This could be because of changes you've made to a bank or config file that make it unreadable. If you think this is the case, consult the [file format](patcher/file_formats.md) documentation for help discovering the issue. It's also possible you have encountered a bug in the program, or a problem with the Raspberry Pi's operating system. In any case, feel free to ask for more help by posting an [issue](https://github.com/albedozero/fluidpatcher/issues) or emailing white2rnado@geekfunklabs.com.
