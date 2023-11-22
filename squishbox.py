#!/usr/bin/env python3
"""SquishBox Raspberry Pi FluidPatcher interface

This script runs FluidPatcher and provides a menu interface using the LCD,
rotary encoder, and stomp switch for loading banks, choosing patches,
and changing settings.

This script can also be imported as a module to create other applications
for the `SquishBox <https://www.geekfunklabs.com/producs/squishbox>`_, or for
any Raspberry Pi connected to a character LCD and either:

- a momentary button (BTN_SW) and rotary encoder (ROT_L, ROT_R, BTN_R)
- *or* just two momentary buttons (BTN_SW, BTN_R)

The `SquishBox` class initializes the character LCD and sets up GPIO pins for
for the encoder, stompswitch, and output pins (including LED). It provides
convenience methods for writing to the LCD, polling inputs/updating the
display, standard menu and input functions, and a few utilities such as
shell command access and wifi control.
"""

__version__ = '0.8.2'

import re
import subprocess
import sys
import threading
import time
import traceback

import RPi.GPIO as GPIO

# squishbox stompswitch
STOMP_MIDICHANNEL = 16
STOMP_MOMENT_CC = 30
STOMP_TOGGLE_CC = 31

# hardware version, set by install script
HW_VERSION = 'v6'

# RPi GPIO pin numbers (BCM numbering) for different hardware versions
ACTIVE = GPIO.LOW
if HW_VERSION == 'v6':
    LCD_RS = 2; LCD_EN = 3; LCD_DATA = 11, 5, 6, 13  # LCD pins
    ROT_L = 22; ROT_R = 10; BTN_R = 9                # rotary encoder R/L pins + button
    BTN_SW = 27; PIN_LED = 17                        # stompbutton and LED
elif HW_VERSION == 'v4':
    LCD_RS = 4; LCD_EN = 17; LCD_DATA = 9, 11, 5, 6
    ROT_L = 2; ROT_R = 3; BTN_R = 27
    BTN_SW = 22; PIN_LED = 10
elif HW_VERSION == 'v3':
    LCD_RS = 4; LCD_EN = 27; LCD_DATA = 9, 11, 5, 6
    ROT_L = 0; ROT_R = 0; BTN_R = 3
    BTN_SW = 2; PIN_LED = 0
elif HW_VERSION == 'v2':
    LCD_RS = 15; LCD_EN = 23; LCD_DATA = 24, 25, 8, 7
    ROT_L = 0; ROT_R = 0; BTN_R = 22
    BTN_SW = 27; PIN_LED = 0
    ACTIVE = GPIO.HIGH
PIN_OUT = PIN_LED, 12, 16, 26 # additional free pins - see SquishBox.gpio_set()

# adjust timings/values below as needed/desired
HOLD_TIME = 1.0
MENU_TIMEOUT = 5.0
BLINK_TIME = 0.1
SCROLL_TIME = 0.4
SCROLL_PAUSE = 4
POLL_TIME = 0.01
BOUNCE_TIME = 0.02
COLS, ROWS = 16, 2

# optional file to customize any of the above settings (and preserve through updates)
try: from hw_overlay import *
except ModuleNotFoundError: pass

# custom characters
c = """\
     |     |     |     |     | ### | # # |  #  \
#    |     |    #|## ##|     |#   #|  #  |  ## \
 #   |     |   ##| ### |##   |  #  | # # |  # #\
  #  | ## #|# ## |  #  |# ###| # # |     |  # #\
   # |#  # |###  | ### |#   #|     |  #  |  #  \
    #|     | #   |## ##|#   #|  #  |     |###  \
     |     |     |     |#####|     |  #  |###  \
     |     |     |     |     |     |     |     \
""".replace('|', '').replace('#', '1').replace(' ', '0')
charbits = [[int(c[i:i + 5], 2) for i in range(j, 320, 40)] for j in range(0, 40, 5)]
BACKSLASH, TILDE, CHECK, XMARK, SUBDIR, WIFIUP, WIFIDOWN, MIDIACT = [chr(i) for i in range(8)]
FNCHARS = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./" + BACKSLASH
USCHARS = ''' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*|/_?.,;:'"`-+=<>()[]{}''' + BACKSLASH + TILDE
# button states
UP = 0; DOWN = 1; HELD = 2
# events
NULL = 0; DEC = 1; INC = 2; SELECT = 3; ESCAPE = 4


class SquishBox():
    """An interface for RPi using character LCD and buttons"""

    def __init__(self):
        """Initializes the LCD and GPIO
        
        Attributes:
          buttoncallback: When the state of a button connected to BTN_SW
            changes, this function is called with 1 if the button was
            pressed, 0 if it was released.
          wificon: contains either the WIFIUP or WIFIDOWN character
            depending on the last-known status of the wifi adapter
        """
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for chan in (ROT_R, ROT_L, BTN_R, BTN_SW):
            if chan:
                pud = GPIO.PUD_UP if ACTIVE == GPIO.LOW else GPIO.PUD_DOWN
                GPIO.setup(chan, GPIO.IN, pull_up_down=pud)
        for chan in (LCD_RS, LCD_EN, *LCD_DATA, *PIN_OUT):
            if chan:
                GPIO.setup(chan, GPIO.OUT)
        for btn in (BTN_R, BTN_SW):
            if btn:
                GPIO.add_event_detect(btn, GPIO.BOTH, callback=self._button_event)
        for enc in (ROT_L, ROT_R):
            if enc:
                GPIO.add_event_detect(enc, GPIO.BOTH, callback=self._encoder_event)
        self.state = {BTN_R: UP, BTN_SW: UP}
        self.timer = {BTN_R: 0, BTN_SW: 0}
        self.encstate = 0b000000
        self.encvalue = 0
        self.buttoncallback = None

        for val in (0x33, 0x32, 0x28, 0x0c, 0x06):
            self._lcd_send(val)
        self.lcd_clear()
        for loc, bits in enumerate(charbits):
            self._lcd_send(0x40 | loc << 3)
            for row in bits:
                self._lcd_send(row, 1)

        self.wificon = WIFIDOWN
        self.wifi_state()
        sys.excepthook = lambda etype, err, tb: self.display_error(err, etype=etype, tb=tb)

    def update(self, idle=POLL_TIME, callback=True):
        """Polls buttons and updates LCD
        
        Call in the main loop of a program to poll the buttons and rotary
        encoder, and update the LCD if necessary. Sleeps for a small amount
        of time before returning so other processes can run.
        Returns an event code based on the state of the buttons. If
        buttoncallback is set and callback=True, the stompswitch calls
        that function instead of sending an event.

        * NULL (0) - no event
        * DEC (1) - stompswitch tapped or encoder rotated counter-clockwise
        * INC (2) - encoder button tapped or encoder rotated clockwise
        * SELECT (3) - encoder button held for HOLD_TIME seconds
        * ESCAPE (4) - stompswitch held for HOLD_TIME seconds

        Args:
          idle: number of seconds to sleep before returning
          callback: if False ignores buttoncallback

        Returns: an integer event code
        """
        callback = self.buttoncallback if callback else None
        t = time.time()
        for r in range(ROWS):
            text = list(self.buffer[r])
            if len(text) > COLS:
                if t > self.scrolltimer:
                    self.scrollpos[r] += 1
                    if self.scrollpos[r] > len(text) - COLS + SCROLL_PAUSE:
                        self.scrollpos[r] = -SCROLL_PAUSE
                i = max(0, self.scrollpos[r])
                i = min(i, len(text) - COLS)
                text = text[i : i+COLS]
            if self.blinktimer > 0:
                for i, c in enumerate(self.blinked[r]):
                    if c:
                        text[i] = c
            self._lcd_putchars(text, r, 0)
        if t > self.scrolltimer:
            self.scrolltimer = time.time() + SCROLL_TIME
        if t > self.blinktimer:
            self.blinked = [[""] * COLS for _ in range(ROWS)]
            self.blinktimer = 0
        event = NULL
        for b in BTN_R, BTN_SW:
            if t - self.timer[b] > BOUNCE_TIME:
                if GPIO.input(b) == ACTIVE:
                    if self.state[b] == UP:
                        self.state[b] = DOWN
                        if b == BTN_SW and callback:
                            callback(1)
                    elif self.state[b] == DOWN and t - self.timer[b] >= HOLD_TIME:
                        self.state[b] = HELD
                        if b == BTN_R: event = SELECT
                        elif b == BTN_SW and not callback: event = ESCAPE
                else:
                    if self.state[b] != UP and b == BTN_SW and callback:
                        callback(0)
                    if self.state[b] == DOWN:
                        if b == BTN_R: event = INC
                        elif b == BTN_SW and not callback: event = DEC
                    self.state[b] = UP
        if self.encvalue > 0: event = INC
        elif self.encvalue < 0: event = DEC
        self.encvalue = 0
        time.sleep(idle)
        return event
        
    def lcd_clear(self):
        """Clear the LCD"""
        self._lcd_send(0x01)
        self._lcd_setcursorpos(0, 0)
        self.buffer = [" " * COLS for _ in range(ROWS)]
        self.written = [[""] * COLS for _ in range(ROWS)]
        self.blinked = [[""] * COLS for _ in range(ROWS)]
        self.scrollpos = [0] * ROWS
        self.scrolltimer = 0
        self.blinktimer = 0
        time.sleep(2e-3)

    def lcd_write(self, text, row, col=0, mode='', now=False):
        """Writes text to the LCD
        
        Writes text to the LCD starting at row, col. Characters are
        stored in a buffer until the user calls update(). Can be
        called with now=True if the LCD needs to be updated now,
        usually because another process would delay updates.

        Args:
          text: string to write
          row: the row at which to start writing
          col: the column at which to start writing
          mode: if 'ljust' or 'rjust' pad with spaces, 'scroll' scrolls
            text to the right if it is long enough, otherwise place text
            starting at row, col
          now: if True update LCD now
        """
        if mode == 'scroll':
            if len(text) > COLS:
                self.buffer[row] = text
                self.scrollpos[row] = -SCROLL_PAUSE
            else:
                mode = 'ljust'
        if mode == 'ljust':
            self.buffer[row] = text[:COLS].ljust(COLS)
        elif mode == 'rjust':
            self.buffer[row] = text[:COLS].rjust(COLS)
        elif mode != 'scroll':
            self.buffer[row] = (self.buffer[row][:col]
                                + text[: COLS-col]
                                + self.buffer[row][col+len(text) :])[:COLS]
        if now: self.update(idle=0)

    def lcd_blink(self, text, row=0, col=0, delay=BLINK_TIME):
        """Blink a character/message on the LCD
        
        Write text on the LCD that disappears after a delay. Text
        written by lcd_write() will reappear. Calling this with
        an empty string removes any current blinks. If a blink
        is already in progress when this is called, the new one
        is ignored.
        
        Args:
          text: string to write, '' to clear blinks
          row: the row at which to place text
          col: the column at which to place text
          delay: time to wait before removing text
        """
        if text == '':
            self.blinked = [[""] * COLS for _ in range(ROWS)]
            self.blinktimer = 0
        elif self.blinktimer == 0:
            for i, c in enumerate(text[: COLS-col]):
                self.blinked[row][col + i] = c
            self.blinktimer = time.time() + delay

    def progresswheel_start(self):
        """Shows an animation while another process runs
        
        Displays a spinning character in the lower right corner of the
        LCD that runs in a thread after this function returns, to give
        the user some feedback while a long-running process completes.
        """
        self.spinning = True
        self.spin = threading.Thread(target=self._progresswheel_spin)
        self.spin.start()
    
    def progresswheel_stop(self):
        """Removes the spinning character"""
        self.spinning = False
        self.spin.join()

    def waitfortap(self, t=0):
        """Waits until a button is pressed or some time has passed
        
        Args:
          t: seconds to wait, if 0 wait forever

        Returns: True if button was pressed, False if time expired
        """
        tstop = time.time() + t
        while True:
            if t and time.time() > tstop:
                return False
            if self.update(callback=False) != NULL:
                return True

    def choose_opt(self, opts, row, i=0, mode='rjust', timeout=MENU_TIMEOUT):
        """Lets the user choose an option from a list
        
        Displays options from a list of choices. User can scroll through
        options with DEC/INC, choose with SELECT, or cancel with ESCAPE
        or timeout. Menu options can scroll.
        
        Args:
          opts: list of strings to display as the choices
          row: the row on which to show the choices
          i: index of the choice to display first
          mode: 'rjust' by default - see lcd_write()
          timeout: seconds to wait, if -1 wait forever

        Returns: index of option chosen, or -1 if canceled
        """
        while True:
            self.lcd_write(opts[i], row, mode=mode)
            t = time.time()
            while timeout == -1 or time.time() - t < timeout:
                event = self.update(callback=False)
                if event == INC:
                    i = (i + 1) % len(opts)
                    break
                elif event == DEC:
                    i = (i - 1) % len(opts)
                    break
                elif event == SELECT:
                    self._lcd_flash(opts[i], row, mode)
                    return i
                elif event == ESCAPE:
                    timeout = 0
            else:
                # self.lcd_write(" " * COLS, row)
                return -1

    def choose_val(self, val, minval, maxval, inc, fmt=f'>{COLS}', timeout=MENU_TIMEOUT, func=None):
        """Lets the user modify a numeric parameter

        Displays a number on the bottom row of the LCD and allows the user to
        scroll its value over a range by specified increment using DEC/INC.
        A function can be called with the current value after each increment
        to demonstrate the result. User can set value with SELECT, or
        cancel with ESCAPE or timeout. 
        
        Args:
          val: the starting value
          minval: the lower limit of the value
          maxval: the upper limit of the value
          inc: the step size to change when incrementing/decrementing the value
          fmt: a format specifier for printing the value nicely
          timeout: seconds to wait, if -1 forever
          func: a function to call with the value every time it changes

        Returns: selected value, or None if time expired or ESCAPE
        """
        while True:
            self.lcd_write(format(val, fmt), ROWS - 1, mode='rjust')
            t = time.time()
            while timeout == -1 or time.time() - t < timeout:
                event = self.update(callback=False)
                if event == INC:
                    val = min(val + inc, maxval)
                    if func: func(val)
                    break
                elif event == DEC:
                    val = max(val - inc, minval)
                    if func: func(val)
                    break
                elif event == SELECT:
                    self._lcd_flash(format(val, fmt), ROWS - 1, mode='rjust')
                    return val
                elif event == ESCAPE:
                    timeout = 0
            else:
                return None

    def confirm_choice(self, text='', row=ROWS-1, timeout=MENU_TIMEOUT):
        """Offers a yes/no choice
        
        Displays some text and lets the user toggle between a check mark
        and an X with DEC/INC and choose with SELECT.
        
        Args:
          text: string to write
          row: the row to display the choice
          timeout: seconds to wait, if -1 wait forever

        Returns: 1 if check is selected, 0 if time expires or ESCAPE
        """
        self.lcd_write(text[:COLS - 1], row)
        c = 1
        while True:
            self.lcd_write([XMARK, CHECK][c], row, COLS - 1)
            t = time.time()
            while timeout == -1 or time.time() - t < timeout:
                event = self.update(callback=False)
                if event in (DEC, INC):
                    c ^= 1
                    break
                elif event == SELECT:
                    if c: self._lcd_flash(text[:COLS], row, mode)
                    return c
                elif event == ESCAPE:
                    timeout = 0
            else:
                return 0

    def char_input(self, text=' ', row=ROWS-1, i=-1,
                   timeout=MENU_TIMEOUT, charset=FNCHARS):
        """Allows user to enter text with a rotary encoder and button

        There are two cursor modes, which are toggled using SELECT. The
        blinking square allows the current character to be changed using
        DEC/INC. The underline cursor changes position with DEC/INC. ESCAPE
        ends edit mode, and allows the user to confirm or cancel the input.

        Args:
          text: the initial text to be edited
          row: the row in which to show the input
          i: initial cursor position, from end if negative
          timeout: seconds to wait before canceling, forever if -1
          charset: the set of allowed characters

        Returns: the edited string, or empty string if canceled
        """
        if i < 0: i = len(text) + i
        c = charset.find(text[i])
        mode = 'line'
        self._lcd_setcursormode(mode)
        while True:
            if mode == 'line':
                self.lcd_write(text[max(0, i+1-COLS) : max(COLS, i+1)],
                               row, mode='ljust', now=True)
            else:
                self.lcd_write(charset[c], row, min(i, COLS-1), now=True)
            self._lcd_setcursorpos(row, min(i, COLS-1))
            t = time.time()
            while timeout == -1 or time.time() - t < timeout:
                event = self.update(callback=False)
                if event == NULL: continue
                if event == INC:
                    if mode == 'line':
                        i = min(i + 1, len(text)) 
                        if i == len(text): text += ' '
                        c = charset.find(text[i])
                    else:
                        c = (c + 1) % len(charset)
                        text = text[0:i] + charset[c] + text[i+1 :]
                elif event == DEC:
                    if mode == 'line':
                        i = max(i - 1, 0)
                        c = charset.find(text[i])
                    else:
                        c = (c - 1) % len(charset)
                        text = text[0:i] + charset[c] + text[i+1 :]
                elif event == SELECT:
                    mode = 'line' if mode == 'blink' else 'blink'
                    self._lcd_setcursormode(mode)
                elif event == ESCAPE:
                    self._lcd_setcursormode('hide')
                    if self.confirm_choice(text.strip()[1-COLS :], row=row):
                        return text.strip().replace(BACKSLASH, '\\').replace(TILDE, '~')
                    else:
                        return ''
                break
            else:
                self._lcd_setcursormode('hide')
                return ''

    def choose_file(self, topdir, last='', ext=None):
        """Lets user browse and select a file on the system
        
        Finds files of a specified type on the file system and lets the
        user choose one using choose_opt(). Timeout is disabled and
        filenames can scroll. Can move up and down through the
        directory tree up to a specified limit. First two arguments must
        be pathlib.Path objects. Shows the current file on the bottom
        row and the current directory on the row above it.

        Args:
          topdir: Path of the highest-level directory the user may see
          last: Path of the file to show as the initial choice
          ext: the file extensions to show, if None shows all files

        Returns: Path of the chosen file or empty string if canceled
        """
        cdir = topdir if last == '' else (last.parent if last.parent > topdir else topdir)
        while True:
            self.lcd_write(f"{str(cdir.relative_to(topdir.parent))}/:", ROWS - 2, mode='scroll')
            x = sorted([p for p in cdir.glob('*') if p.is_dir() or p.suffix == ext or ext == None])
            y = [f"{SUBDIR}{p.name}/" if p.is_dir() else p.name for p in x]
            i = x.index(last) if last in x else 0
            if cdir != topdir:
                x.append(cdir.parent)
                y.append("../")
            j = self.choose_opt(y, ROWS - 1, i, mode='scroll', timeout=-1)
            if j < 0: return ''
            if x[j].is_dir():
                last = cdir
                cdir = x[j]
            else:
                return x[j]

    def display_error(self, err, msg="", etype=None, tb=None):
        """Displays Exception text on the LCD
        
        Reformats the text of an Exception so it can be displayed on one
        line and scrolls it across the bottom row of the LCD, and also prints
        information to stdout. Waits for the user to press a button, then
        returns if possible.

        Args:
          err: the Exception
          msg: an optional error message
        """
        if etype == KeyboardInterrupt:
            sys.exit()
        err_oneline = msg + re.sub(' {2,}', ' ', re.sub('\n|\^', ' ', str(err)))
        self.lcd_write(err_oneline, ROWS - 1, mode='scroll')
        if msg: print(msg)
        if tb:
            traceback.print_exception(etype, err, tb)
        else:
            print(err)
        self.waitfortap()

    @staticmethod
    def shell_cmd(cmd, **kwargs):
        """Executes a shell command and returns the output
        
        Uses subprocess.run to execute a shell command and returns the output
        as ascii with leading and trailing whitespace removed. Blocks until
        shell command has returned.
        
        Args:
          cmd: text of the command line to execute
          kwargs: additional keyword arguments passed to subprocess.run

        Returns: the stripped ascii STDOUT of the command
        """
        return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, shell=True,
                              encoding='ascii', **kwargs).stdout.strip()

    @staticmethod
    def gpio_set(pin, state):
        """Sets the state of a GPIO

        Sets a GPIO high or low, as long as it isn't being used by something
        else. PIN_OUT can be modified to add outputs, as long as they don't
        conflict with those defined above for the LCD, buttons, and GPIOs
        18, 19, and 21 (which are used by the DAC).

        Args:
          pin: pin number (BCM numbering)
          state: True for high, False for low
        """
        if pin in PIN_OUT:
            if state: GPIO.output(pin, GPIO.HIGH)
            else: GPIO.output(pin, GPIO.LOW)

    def wifi_state(self, setstate=''):
        """Checks or sets the state of the wifi adapter
        
        Turns the wifi adapter on or off, or simply returns its current
        state. Does not determine whether it has connected to a network,
        only that it is enabled or disabled.

        Args:
          setstate: 'block' or 'unblock' to set the state, or
            empty string to check current state

        Returns: 'blocked' or 'unblocked'
        """
        if setstate:
            self.shell_cmd(f"sudo rfkill {setstate} wifi")
            state = 'blocked' if setstate == 'block' else 'unblocked'
        else:
            state = self.shell_cmd("rfkill list wifi -o SOFT -rn")
        self.wificon = WIFIDOWN if state == 'blocked' else WIFIUP
        return state

    def wifi_settings(self):
        """Displays a wifi settings menu
        
        Shows the connection status and current IP address(es) of the Pi
        and a list of any available wifi networks. Allows the user to
        enable/disable wifi and enter passkeys for visible networks
        in order to connect.
        """
        self.lcd_clear()
        if ip := sb.shell_cmd("hostname -I"):
            self.lcd_write(f"Connected as {ip}", ROWS - 2, mode='scroll')
        else:
            self.lcd_write("Not connected", ROWS - 2, mode='ljust')
        if self.wifi_state() == 'blocked':
            if self.choose_opt(["Enable WiFi"], row=ROWS - 1) == 0:
                self.wifi_state('unblock')
        else:
            self.lcd_write("scanning ", ROWS - 1, mode='rjust', now=True)
            x = sb.shell_cmd("iw dev wlan0 link")
            ssid = "".join(re.findall('SSID: ([^\n]+)', x))
            opts = [CHECK + ssid] if ssid else []
            self.progresswheel_start()
            try: x = sb.shell_cmd("sudo iw wlan0 scan", timeout=15)
            except subprocess.TimeoutExpired: x = ""
            self.progresswheel_stop()
            networks = set(re.findall('SSID: ([^\n]+)', x))
            opts += [*(networks - {ssid}), "Disable WiFi"]
            j = self.choose_opt(opts, row=ROWS - 1, mode='scroll', timeout=-1)
            if j < 0: return
            elif opts[j] == "Disable WiFi":
                self.wifi_state('block')
            elif j >= 0:
                if CHECK in opts[j]: return
                self.lcd_write("Password:", ROWS - 2, mode='ljust')
                psk = self.char_input(charset = PRNCHARS)
                if psk == '': return
                self.lcd_clear()
                self.lcd_write(opts[j], ROWS - 2, mode='ljust')
                self.lcd_write("adding network ", ROWS - 1, mode='rjust', now=True)
                self.progresswheel_start()
                network = f'\nnetwork={{\n  ssid=\"{opts[j]}\"\n  psk=\"{psk}\"\n}}'
                sb.shell_cmd(f"echo {network} | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf")
                sb.shell_cmd("sudo systemctl restart dhcpcd")
                self.progresswheel_stop()
                self.wifi_settings()

    def _button_event(self, button):
        t = time.time()
        self.timer[button] = t

    def _encoder_event(self, channel):
        for channel in ROT_L, ROT_R:
            self.encstate = (self.encstate << 1) % 64
            self.encstate += 1 if GPIO.input(channel) == ACTIVE else 0
        if self.encstate == 0b111000:
            self.encvalue += 1
        elif self.encstate == 0b110100:
            self.encvalue -= 1

    def _progresswheel_spin(self):
        while True:
            for x in BACKSLASH + '|/-':
                if not self.spinning: return
                self._lcd_putchars(x, ROWS - 1, COLS - 1)
                time.sleep(BLINK_TIME)
                
    def _lcd_flash(self, text, row, mode='', n=3):
        text = text[:COLS].rjust(COLS) if mode == 'rjust' else text[:COLS].ljust(COLS)
        for _ in range(n):
            self._lcd_putchars(' ' * COLS, row, 0)
            time.sleep(BLINK_TIME)
            self._lcd_putchars(text, row, 0)
            time.sleep(BLINK_TIME)

    def _lcd_putchars(self, chars, row, col):
        lastcol = -2
        for c in chars:
            if self.written[row][col] != c:
                if lastcol != col - 1:
                    self._lcd_setcursorpos(row, col)
                self._lcd_send(ord(c), 1)
                self.written[row][col] = c
                lastcol = col
            col += 1

    def _lcd_setcursorpos(self, row, col):
        if row < ROWS and col < COLS:
            offset = [0x00, 0x40, COLS, 0x40 + COLS]
            self._lcd_send(0x80 | offset[row] + col)

    def _lcd_setcursormode(self, mode):
        if mode == 'hide':
            self._lcd_send(0x0c | 0x00)
        elif mode == 'blink':
            self._lcd_send(0x0d)
        elif mode == 'line':
            self._lcd_send(0x0e)

    @staticmethod
    def _lcd_send(val, reg=0):
        GPIO.output(LCD_RS, reg)
        GPIO.output(LCD_EN, GPIO.LOW)
        for nib in (val >> 4, val):
            for i in range(4):
                GPIO.output(LCD_DATA[i], (nib >> i) & 0x01)
            GPIO.output(LCD_EN, GPIO.HIGH)
            time.sleep(50e-6)
            GPIO.output(LCD_EN, GPIO.LOW)

class FluidBox:
    """Manages a SquishBox interface to FluidPatcher"""

    def __init__(self):
        """Creates the FluidBox"""
        self.pno = 0
        self.buttonstate = 0
        fp.midi_callback = self.listener
        sb.buttoncallback = self.handle_buttonevent
        self.midi_connect()
        self.load_bank(fp.currentbank)
        while not fp.currentbank:
            self.load_bank()
        while True:
            self.patchmode()

    def handle_buttonevent(self, val):
        """Handles callback events when the stompbutton state changes
        
        Sends a momentary and toggling MIDI message, and toggles sets the LED
        to match the state of the toggle.
        """
        fp.send_event(f"cc:{STOMP_MIDICHANNEL}:{STOMP_MOMENT_CC}:{val}")
        if val:
            self.buttonstate ^= 1
            fp.send_event(f"cc:{STOMP_MIDICHANNEL}:{STOMP_TOGGLE_CC}:{self.buttonstate}")
            sb.gpio_set(PIN_LED, self.buttonstate)

    def listener(self, sig):
        """Handles MidiSignals from FluidPatcher
        
        Receives MidiSignal instances in response to incoming MIDI events
        or custom events triggered by router rules. MidiSignals for custom
        events have a `val` parameter that is the result of parameter
        routing, and additional parameters corresponding to the rule
        parameters. The following custom rules are handled:

        - `patch`: a patch index to be selected. If `patch` has a '+' or '-'
            suffix, increment the current patch index instead.
        - `lcdwrite`: a string to be written to the LCD, right-justified. If `format`
            is provided, the formatted `val` parameter is appended
        - `setpin`: the *index* of the pin in PIN_OUT to set using `val`. If the LED
            is set, set the state of the button toggle to match
        """
        if 'val' in sig:
            if 'patch' in sig:
                if sig.patch < 0:
                    self.pno = (self.pno + sig.val) % len(fp.patches)
                else:
                    self.pno = sig.patch
            elif 'lcdwrite' in sig:
                if 'format' in sig:
                    val = format(sig.val, sig.format)
                    self.lcdwrite = f"{sig.lcdwrite} {val}"[:COLS].rjust(COLS)
                else:
                    self.lcdwrite = sig.lcdwrite[-COLS:].rjust(COLS)
            elif 'setpin' in sig:
                if PIN_OUT[sig.setpin] == PIN_LED:
                    self.buttonstate = 1 if sig.val else 0
                sb.gpio_set(PIN_OUT[sig.setpin], sig.val)
        else:
            self.lastsig = sig

    def patchmode(self):
        """Selects a patch and displays the main screen"""
        if fp.patches:
            warn = fp.apply_patch(self.pno)
        else:
            warn = fp.apply_patch('')
        pno = self.pno
        while True:
            if fp.patches:
                sb.lcd_write(fp.patches[self.pno], 0, mode='scroll')
                if warn:
                    sb.lcd_write('; '.join(warn), 1, mode='scroll')
                    sb.waitfortap()
                sb.lcd_write(f"patch: {self.pno + 1}/{len(fp.patches)}", 1, mode='rjust')
            else:
                sb.lcd_write("No patches", 0, mode='ljust')
                if warn:
                    sb.lcd_write('; '.join(warn), 1, mode='scroll')
                    sb.waitfortap()
                sb.lcd_write("patch 0/0", 1, mode='rjust')
            sb.lcd_write(sb.wificon, 1, 0)
            warn = []
            self.lastsig = None
            self.lcdwrite = None
            while True:
                if pno != self.pno:
                    return
                if self.lastsig:
                    sb.lcd_blink(MIDIACT, 1, 1)
                    self.lastsig = None
                if self.lcdwrite:
                    sb.lcd_blink('')
                    sb.lcd_blink(self.lcdwrite, 1, delay=MENU_TIMEOUT)
                    self.lcdwrite = None
                event = sb.update()
                if event == NULL:
                    continue
                if event == INC and fp.patches:
                    self.pno = (self.pno + 1) % len(fp.patches)
                    return
                elif event == DEC and fp.patches:
                    self.pno = (self.pno - 1) % len(fp.patches)
                    return
                elif event == SELECT:
                    k = sb.choose_opt(['Load Bank', 'Save Bank', 'Save Patch', 'Delete Patch',
                                       'Open Soundfont', 'Effects..', 'System Menu..'], row=1)
                    if k == 0:
                        if self.load_bank():
                            return
                    elif k == 1:
                        self.save_bank()
                    elif k == 2:
                        sb.lcd_write("Save patch:", 0, mode='ljust')
                        newname = sb.char_input(fp.patches[self.pno])
                        if newname != '':
                            if newname != fp.patches[self.pno]:
                                fp.add_patch(newname, addlike=self.pno)
                            fp.update_patch(newname)
                            self.pno = fp.patches.index(newname)
                    elif k == 3:
                        if sb.confirm_choice('Delete', row=1):
                            fp.delete_patch(self.pno)
                            self.pno = min(self.pno, len(fp.patches) - 1)
                            return
                    elif k == 4:
                        if sfont := sb.choose_file(fp.sfdir, ext='.sf2'):
                            self.sfmode(sfont)                            
                            sb.lcd_write("loading patches ", 1, mode='ljust', now=True)
                            sb.progresswheel_start()
                            fp.load_bank()
                            sb.progresswheel_stop()
                            return
                    elif k == 5:
                        self.effects_menu()
                    elif k == 6:
                        self.system_menu()
                    break

    def sfmode(self, sfont):
        """Soundfont preset chooser"""
        sb.lcd_write(sfont.name, 0, mode='scroll', now=True)
        sb.lcd_write("loading presets ", 1, mode='rjust', now=True)
        sb.progresswheel_start()
        if not (presets := fp.solo_soundfont(sfont)):
            sb.progresswheel_stop()
            sb.lcd_write(f"Unable to load presets from {str(sfont)}", 1, mode='scroll')
            sb.waitfortap()
            return
        sb.progresswheel_stop()
        i = 0
        warn = fp.select_sfpreset(sfont, *presets[i])
        while True:
            bank, prog, name = presets[i]
            sb.lcd_write(name, 0, mode='scroll')
            if warn:
                sb.lcd_write('; '.join(warn), 1, mode='scroll')
                sb.waitfortap()
                warn = []
            sb.lcd_write(f"preset {bank:03}:{prog:03}", 1, mode='rjust')
            while True:
                event = sb.update(callback=False)
                if event == INC:
                    i = (i + 1) % len(presets)
                    warn = fp.select_sfpreset(sfont, *presets[i])
                    break
                elif event == DEC:
                    i = (i - 1) % len(presets)
                    warn = fp.select_sfpreset(sfont, *presets[i])
                    break
                elif event == SELECT:
                    sb.lcd_write("Add as Patch:", 0, mode='ljust')
                    newname = sb.char_input(name)
                    if newname:
                        self.pno = fp.add_patch(newname)
                        fp.update_patch(newname)
                    break
                elif event == ESCAPE: return

    def load_bank(self, bank=""):
        """Bank loading menu"""
        lastbank = fp.currentbank
        lastpatch = fp.patches[self.pno] if fp.patches else ""
        if bank == "":
            last = fp.bankdir / fp.currentbank if fp.currentbank else ""
            bank = sb.choose_file(fp.bankdir, last, '.yaml')
            if bank == "": return False
        sb.lcd_write(bank.name, 0, mode='scroll', now=True)
        sb.lcd_write("loading patches ", 1, mode='ljust', now=True)
        sb.progresswheel_start()
        try: fp.load_bank(bank)
        except Exception as e:
            sb.progresswheel_stop()
            sb.display_error(e, "bank load error: ")
            return False
        sb.progresswheel_stop()
        fp.write_config()
        if fp.currentbank != lastbank:
            self.pno = 0
        else:
            if lastpatch in fp.patches:
                self.pno = fp.patches.index(lastpatch)
            elif self.pno >= len(fp.patches):
                self.pno = 0
        return True

    def save_bank(self, bank=""):
        """Bank saving menu"""
        if bank == "":
            bank = sb.choose_file(fp.bankdir, fp.bankdir / fp.currentbank, '.yaml')
            if bank == "": return
            name = sb.char_input(bank.name)
            if name == "": return
            bank = bank.parent / name
        try: fp.save_bank(bank.with_suffix('.yaml'))
        except Exception as e:
            sb.display_error(e, "bank save error: ")
        else:
            fp.write_config()
            sb.lcd_write("bank saved", 1, mode='ljust')
            sb.waitfortap(2)

    def effects_menu(self):
        """FluidSynth effects setting menu"""
        i=0
        fxmenu_info = (
            # Name             fluidsetting              min    max   inc   format
            ('Reverb Size',   'synth.reverb.room-size',  0.0,   1.0,  0.1, '4.1f'),
            ('Reverb Damp',   'synth.reverb.damp',       0.0,   1.0,  0.1, '4.1f'),
            ('Rev. Width',    'synth.reverb.width',      0.0, 100.0,  0.5, '5.1f'),
            ('Rev. Level',    'synth.reverb.level',     0.00,  1.00, 0.01, '5.2f'),
            ('Chorus Voices', 'synth.chorus.nr',           0,    99,    1, '2d'),
            ('Chor. Level',   'synth.chorus.level',      0.0,  10.0,  0.1, '4.1f'),
            ('Chor. Speed',   'synth.chorus.speed',      0.1,  21.0,  0.1, '4.1f'),
            ('Chorus Depth',  'synth.chorus.depth',      0.3,   5.0,  0.1, '3.1f'),
            ('Gain',          'synth.gain',              0.0,   5.0,  0.1, '11.1f'))
        vals = [fp.fluidsetting_get(info[1]) for info in fxmenu_info]
        fxopts = [fxmenu_info[i][0] + ':' + format(vals[i], fxmenu_info[i][5]) for i in range(len(fxmenu_info))]
        while True:
            sb.lcd_write("Effects:", 0, mode='ljust')
            i = sb.choose_opt(fxopts, 1, i)
            if i < 0:
                break
            sb.lcd_write(fxopts[i], 0, mode='ljust')
            newval = sb.choose_val(vals[i], *fxmenu_info[i][2:], func=lambda x: fp.fluidsetting_set(fxmenu_info[i][1], x))
            if newval != None:
                fp.fluidsetting_set(fxmenu_info[i][1], newval, patch=self.pno)
                vals[i] = newval
                fxopts[i] = fxmenu_info[i][0] + ':' + format(newval, fxmenu_info[i][5])
            else:
                fp.fluidsetting_set(fxmenu_info[i][1], vals[i])

    def system_menu(self):
        """System functions and settings menu"""
        sb.lcd_write("System Menu:", 0, mode='ljust')
        k = sb.choose_opt(['Power Down', 'MIDI Devices', 'Wifi Settings', 'USB File Copy'], row=1)
        if k == 0:
            sb.lcd_write("Shutting down..", 0, mode='ljust')
            sb.lcd_write("Wait 30s, unplug", 1, mode='ljust', now=True)
            sb.shell_cmd("sudo poweroff")
        elif k == 1:
            self.midi_devices()
        elif k == 2:
            sb.wifi_settings()
        elif k == 3:
            self.usb_filecopy()

    def midi_devices(self):
        """Menu for connecting MIDI devices and monitoring"""
        sb.lcd_write("MIDI Devices:", 0, mode='ljust')
        readable = re.findall(" (\d+): '([^\n]*)'", sb.shell_cmd("aconnect -i"))
        rports, rnames = list(zip(*readable))
        p = sb.choose_opt([*rnames, "MIDI monitor.."], row=1, mode='scroll', timeout=-1)
        if p < 0: return
        if 0 <= p < len(rports):
            sb.lcd_write("Connect to:", 0, mode='ljust')
            writable = re.findall(" (\d+): '([^\n]*)'", sb.shell_cmd("aconnect -o"))
            wports, wnames = list(zip(*writable))
            op = sb.choose_opt(wnames, row=1, mode='scroll', timeout=-1)
            if op < 0: return
            if 'midiconnections' not in fp.cfg: fp.cfg['midiconnections'] = []
            fp.cfg['midiconnections'].append({rnames[p]: re.sub('(FLUID Synth) \(.*', '\\1', wnames[op])})
            fp.write_config()
            try: sb.shell_cmd(f"aconnect {rports[p]} {wports[op]}")
            except subprocess.CalledProcessError: pass
        elif p == len(rports):
            sb.lcd_clear()
            sb.lcd_write("MIDI monitor:", 0, mode='ljust')
            msg = self.lastsig
            while not sb.waitfortap(0.1):
                if self.lastsig == msg or self.lastsig == None: continue
                msg = self.lastsig
                if msg.type not in ('note', 'noteoff', 'cc', 'kpress', 'prog', 'pbend', 'cpress'): continue
                t = ('note', 'noteoff', 'cc', 'kpress', 'prog', 'pbend', 'cpress').index(msg.type)
                x = ("note", "noff", "  cc", "keyp", " prog", "pbend", "press")[t]
                if t < 4:
                    sb.lcd_write(f"ch{msg.chan:<3}{x}{msg.par1:3}={msg.par2:<3}", 1)
                else:
                    sb.lcd_write(f"ch{msg.chan:<3}{x}={msg.par1:<5}", 1)

    @staticmethod
    def midi_connect():
        """Make MIDI connections as enumerated in config"""
        devs = {client: port for port, client in re.findall(" (\d+): '([^\n]*)'", sb.shell_cmd("aconnect -io"))}
        for link in fp.cfg.get('midiconnections', []):
            mfrom, mto = list(link.items())[0]
            for client in devs:
                if re.search(mfrom.split(':')[0], client):
                    mfrom = re.sub(mfrom.split(':')[0], devs[client], mfrom, count=1)
                if re.search(mto.split(':')[0], client):
                    mto = re.sub(mto.split(':')[0], devs[client], mto, count=1)
            try: sb.shell_cmd(f"aconnect {mfrom} {mto}")
            except subprocess.CalledProcessError: pass 

    @staticmethod
    def usb_filecopy():
        """Menu for bulk copying files to/from USB drive"""
        sb.lcd_clear()
        sb.lcd_write("USB File Copy:", 0, mode='ljust')
        usb = re.search('/dev/sd[a-z]\d*', sb.shell_cmd("sudo blkid"))
        if not usb:
            sb.lcd_write("USB not found", 1, mode='ljust')
            sb.waitfortap(2)
            return
        opts = ['USB -> SquishBox', 'SquishBox -> USB', 'Sync with USB']
        j = sb.choose_opt(opts, row=1)
        if j < 0: return
        sb.lcd_write(opts[j], row=0, mode='ljust')
        sb.lcd_write("copying files ", 1, mode='rjust', now=True)
        sb.progresswheel_start()
        try:
            sb.shell_cmd("sudo mkdir -p /mnt/usbdrv")
            sb.shell_cmd(f"sudo mount -o owner,fmask=0000,dmask=0000 {usb[0]} /mnt/usbdrv/")
            if j == 0:
                sb.shell_cmd("rsync -rtL /mnt/usbdrv/SquishBox/ SquishBox/")
            elif j == 1:
                sb.shell_cmd("rsync -rtL SquishBox/ /mnt/usbdrv/SquishBox/")
            elif j == 2:
                sb.shell_cmd("rsync -rtLu /mnt/usbdrv/SquishBox/ SquishBox/")
                sb.shell_cmd("rsync -rtLu SquishBox/ /mnt/usbdrv/SquishBox/")
            sb.shell_cmd("sudo umount /mnt/usbdrv")
        except Exception as e:
            sb.progresswheel_stop()
            sb.display_error(e, "halted - errors: ")
        else:
            sb.progresswheel_stop()


if __name__ == "__main__":

    import os

    from fluidpatcher import FluidPatcher
    
    os.umask(0o002)
    sb = SquishBox()
    sb.lcd_clear()
    try: fp = FluidPatcher("SquishBox/squishboxconf.yaml")
    except Exception as e:
        sb.display_error(e, "bad config file: ")
    else:
        mainapp = FluidBox()
        mainapp.patchmode()
