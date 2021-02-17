# Utilities

These files contain code that is used in the _implementations_ of patcher (i.e squishbox.py, headlesspi.py, fluidpatcher.pyw) but not patcher itself.

## stompboxpi.py

This module creates a StompBox object that reads the buttons and controls the LCD connected to a Raspberry Pi, and is used by squishbox.py. The variables imported from _hw_overlay.py_ store what pins on the GPIO header these things are connected to. It uses RPLCD and RPi.GPIO to control them. Create a _StompBox_ object to initialize the LCD, and call its _update()_ method in the main loop of your code to update the display and poll the buttons. Other methods (described below) allow you to write text to the LCD, query the user for a choice between options, input a number or text string, etc.

Each button can be in different states depending on how long it has been held down, which you check using the _button()_ method. The ones to check for are:
- _UP_: the button is not pressed
- _TAP_: the button was just released after being pressed for a short time
- _HOLD_: the button has been held down for exactly _HOLD_TIME_ (~1s)
- _LONG_: the button has been held down for exactly _LONG_TIME_ (~3s)

### class StompBox

**StompBox**()

A Python object that acts as an interface for two buttons and a 16x2 character LCD connected to a Raspberry Pi

#### Methods:

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

To use this for your own purposes, import `netlink` in the two scripts that you want to communicate. You can implement your own request types and change the default port, passkey, and buffer size if needed. Create a _Server_ object in one script to listen for connections. Create a _Client_ object in the other script to connect to the server script. Call the _request_ method on the client to talk to the server and get a _Message_ object with the reply in its _body_ attribute. On the server, call _pending_ in the main loop of your program to get requests from clients as a list of _Message_ objects. After dealing with a request, call the _reply_ method of the server to respond.

### class Message

Message objects are used by clients and servers to encode requests and replies into text streams that can be sent via sockets. You don't need to create them yourself - they are created internally when you call _Client.request()_ and _Server.reply()_.

#### Public Attributes:
- _type_: one of the integer constants defined at the top of _netlink.py_
- _body_: the text of the request or reply
- _id_: Each request has a unique ID - the server tags its responses with the request ID so that the client can match responses with requests

### class Server

**Server**(_port=DEFAULT_PORT, passkey=DEFAULT_PASSKEY_)

Sets up a server listening on _port_. The _passkey_ must be the same on client and server, and can be up to 7 characters.

#### Methods:
  
**pending**()

Checks to see if any clients have connected and made requests. Returns the current queue of requests as a list of _Message_ objects.

**reply**(_req, response='', type=REQ_OK_)

Sends a reply to the client that sent _req_, with _response_ as the message body.

### class Client

**Client**(_server='', port=DEFAULT_PORT, passkey=DEFAULT_PASSKEY, timeout=20_)

Starts a client and connects to IP address _server_ on _port_ with _passkey_.

#### Methods:

**request**(_type, body='', blocking=1_)

Sends a request to the server, where message _type_ is one of the integer constants defined at the top of the file. If _blocking_ evaluates as **True**, waits until the server responds and returns the response as a _Message_ object.

**check**()

Checks to see if a reply to any non-blocking requests has arrived. If so, remove the request from the list and return a _Message_ object for the response.
