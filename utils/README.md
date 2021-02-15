# Utilities

These files contain code that is used in the _implementations_ of patcher (i.e squishbox.py, headlesspi.py, fluidpatcher.pyw) but not patcher itself.

## stompboxpi.py

This module creates a StompBox object that reads the buttons and controls the LCD connected to a Raspberry Pi, and is used by squishbox.py. The variables imported from hw_overlay.py store what pins on the GPIO header these things are connected to. It uses RPLCD and RPi.GPIO to control them. Create a StompBox object to initialize the LCD, and call its _update()_ method in the main loop of your code to update the display and poll the buttons. Other methods (described below) allow you to write text to the LCD, query the user for a choice between options, input a number or text string, etc.

Each button can be in different states depending on how long it has been held down, which you check using the _button()_ method. The ones to check for are:
- _UP_: the button is not pressed
- _TAP_: the button was just released after being pressed for a short time
- _HOLD_: the button has been held down for exactly _HOLD_TIME_ (~1s)
- _LONG_: the button has been held down for exactly _LONG_TIME_ (~3s)

### class StompBox

**StompBox**()

A Python object that acts as an interface for two buttons and a 16x2 character LCD connected to a Raspberry Pi

**button**(_self, button_)

Get the current state of a button by name

**buttons**(_self_)

Return a list of the states of all buttons

**waitforrelease**(_self, tmin=0_)

Wait for all buttons to be released and at least _tmin_ seconds

**waitfortap**(_self, t_)

Wait _t_ seconds or until a button is tapped. Returns _True_ if tapped, _False_ if not

**lcd_clear**(_self_)

Clears the LCD

**lcd_write**(_self, text, row=0, col=0_)

Writes _text_ starting on the given _row_ beginning at _col_. If the text is longer than 16 characters, it will scroll.

**lcd_blink**(_self, text, row=0, n=3_)

Writes _text_ to _row_ and blinks it _n_ times.

**choose_opt**(_self, opts, row=0, timeout=MENU_TIMEOUT, passlong=False_)

Allows the user to choose between different _opts_ by tapping buttons to scroll through them. Holding right will confirm, blink the choice, and return the index of the option chosen. Holding left or waiting longer than _timeout_ will cancel and return -1. If _passlong_ is _True_, and the user has been holding the button since _choose_opt_ was called, for a total of _LONG_TIME_ seconds, the method returns -1 so this state can be processed by the main loop. If _passlong_ is _False_ long button holds are ignored.

**choose_val**(_self, val, inc, minval, maxval, format="%16s"_)

Lets the user choose a numeric value between _minval_ and _maxval_, with a starting value of _val_. Tapping buttons increases or decreases the value by _inc_, and holding buttons increments the value quickly. The value is displayed according to _format_. The value is returned when the user waits ~5s without pressing a button.

**char_input**(_self, text='', row=1, timeout=MENU_TIMEOUT, charset=INPCHARS)

Allows a user to enter text strings charater by character. Tapping buttons changes the current character, and holding a button down moves the cursor. When the user moves the cursor to the end of the string they can also choose the accept and delete characters. Holding right on accept will return the text, and waiting ~5s cancels the text entry.

### Example

```python
from utils import stompboxpi as SB

sb = SB.StompBox()
sb.lcd_clear()

x=0
pets = ['cat', 'dog', 'fish']
while True:
    sb.lcd_write("Hello world! This is a line of scrolling text.")
    sb.lcd_write("%16s" % x, row=1, col=0)
    while True:
        sb.update()
        if SB.TAP in sb.buttons(): 
            if sb.button('right') == SB.TAP:
                x += 1
                break
            elif sb.button('left'):
                x -= 1
                break
        if SB.HOLD in sb.buttons():
            sb.lcd_clear()
            sb.lcd_write("Choose your pet:")
            i = sb.choose_opt(pets, row=1, passlong=True)
            if i >= 0:
                print(pets[i])
            break
        if SB.LONG in sb.buttons():
            sb.lcd_clear()
            sb.lcd_write("Bye!")
            exit()
```

## netlink.py

This code implements a simple client/server architecture using sockets that is used by fluidpatcher.pyw (client) to communicate with a running instance of squishbox.py or headlesspi.py (server). This allows fluidpatcher.pyw to be used as a graphical tool for configuring the SquishBox or headless Pi synth, and for creating/editing/testing patches.

