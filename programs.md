# Included Programs


This document explains how to set up and use the programs included in this repository. For information on creating and editing patches and bank files, consult [file_formats.md](patcher/file_formats.md). The [Patcher API](patcher/README.md) documentation provides information on modifying these programs or creating new implementations. For info on installing software, see [README.md](README.md).

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

To safely shut down the Pi when the script is set to run on startup without a keyboard or remote connection, press and hold either the _INC_PATCH_ or _DEC_PATCH_ control for approximately 7 seconds. After 5 seconds, the red power LED starts blinking to warn a shutdown is about to occur, and the green activity LED will begin flickering as the shutdown process happens. Once the green activity LED goes dark, the Pi can be safely unplugged.


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

When activated, the current firmware version is displayed while the last-used bank is loaded. The current patch name, number, and total patches available are displayed on the LCD. 

### Navigating Patches/Menus

The unit can be controlled with a left/right pair of buttons/momentary switches or a pushbutton rotary encoder. Tapping (pressing and releasing quickly) the left or right buttons cycles through patches, as does rotating the encoder. An option is selected by holding the right button for approximately one second, or tapping the rotary encoder button. Holding the left button or rotary pushbutton down for one second cancels or goes back to the previous screen.

- From the patch screen, holding the right button for approximately one second or tapping the rotary encoder pushbutton opens the menu. Holding the left button or rotary pushbutton for one second will give the option to Restart, which actually quits the program. By default, the SquishBox is set up to automatically restart the software, so this can provide a way to stop sound and reset the synthesizer in case of stuck notes or some other problem.
- When asked to confirm a choice, the choice will appear with a checkmark next to it. Tap left/right or rotate the encoder to switch between the checkmark for confirm and X for cancel. Make your choice by long-pressing right or tapping the encoder.
- Some menus allow you to change a numerical setting. Tapping the left or right buttons or rotating the encoder increases/decreases the value. Long-press right or tap the encoder to confirm, or long-press the encoder or left button to cancel.
- Some menus allow you to enter text character-by-character. The cursor has two modes - an underline and a blinking square. Tap the encoder or long-press right to toggle cursor modes. The underline cursor lets you change the cursor position, and the blinking square cursor lets you change the current character. Long-press the encoder or left button when finished. You will be asked to confirm your entry.

### Menu Options

- **Load Bank** – Load a bank file from the list of available banks. The current bank is displayed first.
- **Save Bank** – Save the current bank. Changing the name saves as a new bank.
- **Save Patch** – Saves the current state of the synthesizer (instrument settings, control change values) to the current patch. Modify the name to create a new patch.
- **Delete Patch** – Erases the current patch from the bank, after asking for confirmation.
- **Open Soundfont** – Opens a single soundfont and switches to playing sounds from the soundfont's presets instead of the patches in the current bank. The unit can be returned to playing patches by long-pressing the encoder or left button. In soundfont mode, the available menu options are:
  - **Add as Patch** - Creates a new patch in the current bank that uses the selected preset. This allows you to create new patches directly from the SquishBox.
  - **Open Soundfont** - Opens a different soundfont.
  - **Load Bank** - Leaves soundfont mode and loads a bank file.
- **Effects..** – Opens a menu that allows you to modify the settings of the chorus and reverb effects units, and the gain (maximum output volume) of the SquishBox. Changes affect all patches in the bank – save the bank to make them permanent.
- **System Menu..** - Opens a menu with more system-related tasks:
  - **Power Down** – To protect the memory card of the SquishBox, this option should be used before unplugging. Allow 30 seconds for complete shutdown.
  - **MIDI Devices** – This menu can be used to view the list of available MIDI devices, and to interconnect MIDI inputs and outputs. By default, the SquishBox automatically connects to all available MIDI devices, but this could be used to send MIDI messages to an additional external device. It also includes a _MIDI Monitor_ option that displays incoming MIDI messages on the screen. Pressing any button closes the MIDI monitor.
  - **WIFI Settings** – Displays the current IP Address of the SquishBox, and provides a menu to scan for and connect to available WIFI networks.
  - **Add From USB** – This option provides a quick, simple way of copying files to the SquishBox. It will search for any connected USB storage devices and copy their entire contents, preserving directory structure, to the _SquishBox/_ folder, overwriting files with the same name. Soundfonts, banks, and MIDI/SYSEX files should be staged on the USB drive in _sf2/, banks/_, and _midi/_ folders, respectively.
  - **Update Device** - This will connect to the internet to check for updates to the SquishBox/FluidPatcher software and/or the Raspberry Pi OS, and give the user the option to update if available. Updating will take some time while the SquishBox downloads and installs software, then reboots. The process is complete once the SquishBox restarts and displays the current patch.
