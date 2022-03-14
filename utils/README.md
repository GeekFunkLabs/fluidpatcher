# Utilities

These files contain code that is used in the _implementations_ of patcher (i.e squishbox.py, headlesspi.py, fluidpatcher.pyw) but not patcher itself.

## stompboxpi.py

This module creates a StompBox object that reads the buttons and/or rotary encoder and controls the LCD connected to a Raspberry Pi, and is used by squishbox.py. Create a _StompBox_ object to initialize the LCD, and call its _update()_ method in the main loop of your code to update the button/encoder states. Other methods (described below) allow you to write text to the LCD, query the user for a choice between options, input a number or text string, etc. The constants below are used to define how the LCD and buttons/encoder are connected to the Raspberry Pi, and are read from _hw_overlay.py_.

constant                       | definition
-------------------------------|--------------------------------
LCD_RS                         | LCD reset pin
LCD_EN                         | LCD enable pin
LCD_D4, LCD_D5, LCD_D6, LCD_D7 | LCD data pins D4-D7
COLS, ROWS                     | The number of columns and rows on the LCD
BTN_L, BTN_R                   | left and right stompbuttons*
ROT_L, ROT_R, BTN_ROT          | rotary encoder pins*
BTN_SW                         | a button or list of buttons that trigger a callback function*
PIN_OUT                        | a list of GPIO pins that are allowed to be set by **gpio_set**, e.g. for LEDs*
ACTIVE_HIGH                    | 1=buttons connect to 3.3V; 0=buttons connect to ground

*omit or set to 0 if not connected  

The constants _HOLD_TIME, MENU_TIMEOUT, BLINK_TIME, SCROLL_TIME, POLL_TIME, BOUNCE_TIME_ at the top of _squishbox.py_ can be modified as desired, or redefined in hw_overlay.py

### class StompBox

**StompBox**()

A Python object that acts as an interface for buttons/encoder and a 16x2 character LCD connected to a Raspberry Pi.

#### Public Attributes:

**buttoncallback**

The function to call when the buttons connected to _PIN_SW_ are pressed or released. The function should take two arguments, the pin number of the button that triggered the callback, and a value corresponding to the button state (1=pressed, 0=released).

#### Methods:

**update**()

Call this in the main loop of your program to scroll the LCD display and check the state of the buttons/rotary encoder. Also sleeps for _POLL_TIME_ seconds to allow other threads (e.g. FluidSynth) to run. Returns an event code depending on the state of the controls.
- _NULL_: no event
- _RIGHT_: right button tapped or encoder rotated clockwise
- _LEFT_: left button tapped or encoder rotated counter-clockwise
- _SELECT_: open a menu/confirm a choice - right button pressed ~1s or encoder knob tapped
- _ESCAPE_: exit a menu/cancel a choice - left button or encoder knob pressed ~1s

**waitfortap**(_t=0_)

Wait _t_ seconds or until a button is tapped. If _t_ is not given, wait forever. Returns _True_ if tapped, _False_ if not

**lcd_clear**()

Clears the LCD

**lcd_write**(_text, row=0, scroll=False, rjust=False, now=False_)

Writes _text_ to _row_, right-justified if _rjust_ is _True_. If the text is longer than 16 characters and _scroll_ is true, the text will scroll. The text is not actually written until the next **update()**, unless _now=True_.

**lcd_blink**(_text, row=0, n=3, rjust=False_)

Writes _text_ to _row_ and blinks it _n_ times.

**progresswheel_start**()

Show a spinning progress wheel in the lower right corner of the display. Keeps spinning after the function returns so the main program can do things.

**progresswheel_stop**()

Stop and remove the spinning progress wheel.

**confirm_choice**(_text='', row=1, timeout=MENU_TIMEOUT_)

Displays _text_ and allows the user to toggle between a checkmark or an X. Returns 1 if the user selects the checkmark, 0 otherwise.

**choose_opt**(_opts, i=0, row=0, scroll=False, timeout=MENU_TIMEOUT, rjust=False_)

Allows the user to choose from a list of _opts_. The index _i_ sets the initial option. Returns the index of the option selected. Canceling or waiting longer than _timeout_ returns -1.

**choose_val**(_val, inc, minval, maxval, fmt=f'>{COLS}', timeout=MENU_TIMEOUT_)

Lets the user choose a numeric value between _minval_ and _maxval_, with a starting value of _val_. The value is displayed according to _fmt_. _RIGHT_ or _LEFT_ changes the value by _inc_. Returns the value selected. Canceling or timing out returns _None_.

**char_input**(_text='', i=-1, row=1, timeout=MENU_TIMEOUT, charset=INPCHARS_)

Allows a user to enter text strings charater by character. _SELECT_ toggles the cursor type. The underline cursor allows moving the insert point, the blink cursor allows changing the current character. _ESCAPE_ ends the text input, and asks the user to confirm the modified text via **confirm_choice()**.

**gpio_set**(_n, state_)

Sets the state of the _n_th pin in _PIN_OUT_ to _state_. 1=on; 0=off

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
