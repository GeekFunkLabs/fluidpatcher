# Utilities

These files contain code that is used in the _implementations_ of patcher (i.e squishbox.py, headlesspi.py, fluidpatcher.pyw) but not patcher itself.

## stompboxpi.py

This module creates a StompBox object that reads the buttons and/or rotary encoder and controls the LCD connected to a Raspberry Pi, and is used by squishbox.py. It uses RPLCD and RPi.GPIO to control them. Create a _StompBox_ object to initialize the LCD, and call its _update()_ method in the main loop of your code to update the display and poll the buttons. Other methods (described below) allow you to write text to the LCD, query the user for a choice between options, input a number or text string, etc.

### class StompBox

**StompBox**()

A Python object that acts as an interface for two buttons and a 16x2 character LCD connected to a Raspberry Pi

#### Methods:

**update**()

Call this regularly to scroll the LCD display and check the state of the buttons/rotary encoder. Returns an event code depending on the state of the buttons/encoder.
- _NULL_: no event
- _RIGHT_: right button tapped or encoder rotated clockwise
- _LEFT_: left button tapped or encoder rotated counter-clockwise
- _SELECT_: open a menu/confirm a choice - right button pressed ~1s or encoder knob tapped
- _ESCAPE_: exit a menu/cancel a choice - left button or encoder knob pressed ~1s

**waitforrelease**(_self, tmin=0_)

Wait for all buttons to be released and at least _tmin_ seconds

**waitfortap**(_self, t_)

Wait _t_ seconds or until a button is tapped. Returns _True_ if tapped, _False_ if not

**lcd_clear**(_self_)

Clears the LCD

**lcd_write**(_self, text, row=0, scroll=False, rjust=False_)

Writes _text_ to _row_, right-justified if _rjust_ is _True_. If the text is longer than 16 characters and _scroll_ is true, the text will scroll.

**lcd_blink**(_self, text, row=0, n=3, rjust=False_)

Writes _text_ to _row_ and blinks it _n_ times.

**confirm_choice**(_self, text='', row=1, timeout=MENU_TIMEOUT_)

Displays _text_ and allows the user to toggle between a checkmark or an X. Returns 1 if the user selects the checkmark, 0 otherwise.

**choose_opt**(_self, opts, i=0, row=0, scroll=False, timeout=MENU_TIMEOUT, rjust=False_)

Allows the user to choose from a list of _opts_. The index _i_ sets the initial option. Returns the index of the option selected. Canceling or waiting longer than _timeout_ will returns -1. 

**choose_val**(_self, val, inc, minval, maxval, fmt=f'>{COLS}', timeout=MENU_TIMEOUT_)

Lets the user choose a numeric value between _minval_ and _maxval_, with a starting value of _val_. The value is displayed according to _fmt_. _RIGHT_ or _LEFT_ changes the value by _inc_. Returns the value selected. Canceling or timing out returns _None_.

**char_input**(_self, text='', i=-1, row=1, timeout=MENU_TIMEOUT, charset=INPCHARS_)

Allows a user to enter text strings charater by character. _SELECT_ toggles the cursor type. The underline cursor allows moving the insert point, the blink cursor allows changing the current character. _ESCAPE_ ends the text input, and asks the user to confirm the modified text via **confirm_choice()**.

### Example

```python
from utils import stompboxpi as SB

sb = SB.StompBox()
sb.lcd_clear()

x=0
pets = ['cat', 'dog', 'fish']
while True:
    sb.lcd_write("Hello world! This is a line of scrolling text.", scroll=True)
    sb.lcd_write(x, row=1)
    while True:
        event = sb.update()
        if event == SB.RIGHT:
			x += 1
			break
		elif event == SB.LEFT:
			x -= 1
			break
        elif event == SB.SELECT:
            sb.lcd_clear()
            sb.lcd_write("Choose your pet:")
            i = sb.choose_opt(pets, row=1)
            if i >= 0:
                print(pets[i])
            break
        elif event == SB.ESCAPE:
            sb.lcd_clear()
            sb.lcd_write("Bye!")
            exit()
```
