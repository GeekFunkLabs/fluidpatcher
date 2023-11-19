# Included Programs


This document explains how to set up and use the programs included in this repository. For information on creating and editing patches and bank files, consult [file_formats.md](fluidpatcher/file_formats.md). The [FluidPatcher API](fluidpatcher/README.md) documentation provides information on modifying these programs or creating new implementations. For info on installing software, see [README.md](README.md).

## headlesspi.py

This script, when it's set to run on startup, turns a Raspberry Pi into a standalone MIDI sound module. It's more minimalistic than the SquishBox, but doesn't require any extra hardware other than the Pi and a MIDI controller. It uses _SquishBox/squishboxconf.yaml_ by default, but will use an alternate config file if given as a command-line argument.

Plug in headphones and your MIDI controller and start up your Raspberry Pi. The Pi's built-in LEDs are used for visual feedback. When ready to play, the green activity LED will blink five times. It will blink once when switching patches, and when changing banks will glow steadily until the bank is loaded. The red power LED remains on when the synth is active, but will blink in a repeating pattern if an error occurs. If you encounter errors or other issues with _headlesspi.py_, see the [troubleshooting](troubleshooting.md) document.
- 2 blinks = error in config file
- 3 blinks = error in bank file
- 4 blinks = other error

Switching between patches and loading different banks is accomplished using the MIDI controller. Many MIDI controllers have pads or knobs that can be assigned to send control change (CC) messages. The script listens for the specific messages described by variables defined at the top of the file:

```python
CTRLS_MIDI_CHANNEL = 1
DEC_PATCH = 21          # decrement the patch number
INC_PATCH = 22          # increment the patch number
SELECT_PATCH = 23       # choose a patch using a knob or slider
BANK_INC = 24           # load the next bank
```

These values can be modified to match a MIDI controller's settings, or the MIDI controller can be reprogrammed to send these CC messages. The script can also be made to listen for note messages (or any type of MIDI message) to change patches by modifying the `connect_controls()` function. The controller should send these as "momentary" messages i.e. send an on/positive value when a key/pad is pressed and off/zero when released.

To safely shut down the Pi when the script is set to run on startup without a keyboard or remote connection, press and hold either the _INC_PATCH_ or _DEC_PATCH_ control for approximately 7 seconds. After 5 seconds, the red power LED starts blinking to warn a shutdown is about to occur, and the green activity LED will begin flickering as the shutdown process happens. Once the green activity LED goes dark, the Pi can be safely unplugged. The value of `SHUTDOWN_BTN` can be set to use a different control from the patch buttons.


## fluidpatcher.pyw

_Fluidpatcher.pyw_ is a desktop (GUI) program that should work on any platform (Windows, Linux, MacOS) where Python 3 and FluidSynth can be installed. It can be used to play patches in a live setting, and also to edit bank files and immediately hear the results.

The _fluidpatcher.pyw_ script takes a config file as its argument, otherwise it will use _fluidpatcherconf.yaml_ by default. The main UI consists of a display showing the current bank and patch, and buttons for switching patches or loading the next available bank. The menus provide options for loading/saving bank files, and selecting patches. The _Tools_ menu provides useful features:

- _Edit Bank_ - Opens a separate text editor window in which the current bank can be edited directly. Clicking "Apply" will scan the text and update the bank, or pop up a message if there are errors.
- _Choose Preset_ - Opens a soundfont, and allows the user to scroll through and play the soundfont's presets. Double-clicking or clicking "OK" will paste the selected preset into the bank file.
- _MIDI Monitor_ - Opens a dialog that will display received MIDI messages
- _Fill Screen_ - Hides the menu bar and maximizes the main UI. Can be useful in live playing.
- _Settings_ - Opens a dialog for viewing and editing the contents of the current config file. The program must be restarted for the changes to take effect.

Some program settings, such as the initial height, width, and font size of the UI, can be adjusted by editing the script itself and changing the values of _WIDTH, HEIGHT, FONTSIZE, PAD, FILLSCREEN_ at the beginning of the file.


## squishbox.py

The _squishbox.py_ script is written to run on a Raspberry Pi in standard effects pedal enclosure with buttons and/or a rotary encoder and a 16x2 character LCD, creating a complete open source MIDI sound module. The [SquishBox](http://geekfunklabs.com/hardware/squishbox/) is designed by [Geek Funk Labs](http://geekfunklabs.com/), where you can find information on downloading software, building your own, or obtaining a fully constructed unit.

On startup, the FluidPatcher version is displayed while the last-used bank loads. The current patch name, number, and total patches available are displayed on the LCD. You scroll through patches using the encoder. You can also tap the encoder to advance to the next patch. The stompbutton sends MIDI messages that can be routed in banks or patches to act as a pedal, effects control, or perform other actions. The messages sent are control change 30 with a value of 127 and 0 on press and release, and control change 31 toggling between 0 and 127 with each press. 

### Navigating Patches/Menus

The unit is controlled with a momentary buttons and a pushbutton rotary encoder. Rotating the encoder cycles through patches. The encoder can also be tapped to advance to the next patch. The stompbutton sends MIDI messages that can be routed in banks or patches to act as a pedal, effects control, or perform other actions. The messages sent are control change 30 with a value of 127 and 0 on press and release, and control change 31 toggling between 0 and 127 with each press.

Holding down the rotary encoder for one second opens the menu. In menus the stompbutton does not send MIDI messages. Instead, rotating the encoder scrolls through options, or tapping the encoder advances to the next option and tapping the stompbutton goes back. This makes it easier to use the SquishBox with feet if it’s placed on the floor. Holding the encoder for one second selects options, and holding the stompbutton for one second cancels or exits. Most menus will time out after a few seconds with no input.

Some menus have specific interaction modes:
- When asked to confirm a choice, it will be shown with a check mark or X next to it. Selecting the check mark confirms, X cancels. 
- Some menus allow changing a numerical setting. Rotating the encoder adjusts the value, and holding the encoder confirms it.
- Some menus allow entering text character-by-character. The cursor appears as an underline for changing position and a blinking square for changing the current character. Holding the encoder switches between cursor modes. Holding the stompbutton exits editing, after which you will be asked to confirm or cancel your entry.

### Menu Options

- **Load Bank** – Load a bank file from the list of available banks. The current bank is displayed first.
- **Save Bank** – Save the current bank. Changing the name saves as a new bank.
- **Save Patch** – Saves the current state of the synthesizer (instrument settings, control change values) to the current patch. Modify the name to create a new patch. Save the bank to make new patches permanent.
- **Delete Patch** – Erases the current patch from the bank, after asking for confirmation.
- **Open Soundfont** – Opens a single soundfont and switches to playing sounds from the soundfont's presets instead of the patches in the current bank. Presets can be copied to the current bank as new patches.
- **Effects..** – Opens a menu that allows you to modify the settings of the chorus and reverb effects units, and the gain (maximum output volume) of the SquishBox. Changes affect all patches in the bank – save the bank to make them permanent.
- **System Menu..** - Opens a menu with more system-related tasks:
  - **Power Down** – To protect the memory card of the SquishBox, this option should be used before unplugging. Allow 30 seconds for complete shutdown.
  - **MIDI Devices** – This menu can be used to view the list of available MIDI devices, and to interconnect MIDI inputs and outputs. By default, the SquishBox automatically connects to all available MIDI devices, but this could be used to send MIDI messages to an additional external device. It also includes a _MIDI Monitor_ option that displays incoming MIDI messages on the screen. Pressing any button exits the MIDI monitor.
  - **Wifi Settings** – Displays the current IP Address of the SquishBox, and provides a menu to scan for and connect to available WIFI networks.
  - **USB File Copy** – Allows you to copy your banks, soundfonts, and config files back and forth between the SquishBox and a USB storage device. Files are copied to/from a _SquishBox/_ folder on the USB. The **Sync with USB** option will update the files to the newest available version on either device.
