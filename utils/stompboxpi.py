"""
Description: python interface for a raspberry pi with two gpio buttons and a 16x2 character LCD
"""

# adjust timings below as needed/desired
HOLD_TIME = 1.0
MENU_TIMEOUT = 5.0
BLINK_TIME = 0.1
SCROLL_TIME = 0.4
POLL_TIME = 0.01
BOUNCE_TIME = 0.02

import time, threading
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD

COLS, ROWS = 16, 2
BTN_L, BTN_R, ROT_L, ROT_R, BTN_ROT, BTN_SW, PIN_OUT = 0, 0, 0, 0, 0, (), ()
from .hw_overlay import *
ACTIVE = GPIO.HIGH if ACTIVE_HIGH else GPIO.LOW
if isinstance(PIN_OUT, int): PIN_OUT = (PIN_OUT, )
if isinstance(BTN_SW, int): BTN_SW = (BTN_SW, )
BUTTONS = [x for x in (BTN_L, BTN_R, BTN_ROT, *BTN_SW) if x]

# events
NULL = 0
LEFT = 1
RIGHT = 2
SELECT = 3
ESCAPE = 4

# button states
UP = 0
DOWN = 1
HELD = 2

# custom lcd characters
XMARK = chr(0)
CHECK = chr(1)
BACKSLASH = chr(2)
PADLEFT = chr(7)
PADRIGHT = chr(8)
XMARK_BITS = (
0b00000,
0b11011,
0b01110,
0b00100,
0b01110,
0b11011,
0b00000,
0b00000)
CHECK_BITS = (
0b00000,
0b00001,
0b00011,
0b10110,
0b11100,
0b01000,
0b00000,
0b00000)
BACKSLASH_BITS = (
0b00000,
0b10000,
0b01000,
0b00100,
0b00010,
0b00001,
0b00000,
0b00000)
INPCHARS = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.\/"
PRNCHARS = ''' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'''

class StompBox():

    def __init__(self):
    
        # initialize LCD
        self.LCD = CharLCD(pin_rs=LCD_RS,
                            pin_e=LCD_EN,
                            pin_rw=None,
                            pins_data=[LCD_D4, LCD_D5, LCD_D6, LCD_D7],
                            numbering_mode=GPIO.BCM,
                            cols=COLS, rows=ROWS,
                            compat_mode=True)
        self.LCD.create_char(ord(XMARK), XMARK_BITS)
        self.LCD.create_char(ord(CHECK), CHECK_BITS)
        self.LCD.create_char(ord(BACKSLASH), BACKSLASH_BITS)
        self.lcd_clear()
        self.lastscroll = time.time()

        # set up buttons
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for channel in (*BUTTONS, ROT_R, ROT_L):
            if channel:
                if ACTIVE == GPIO.HIGH:
                    GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                else:
                    GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        for pin in PIN_OUT: GPIO.setup(pin, GPIO.OUT)
        self.state = {button: DOWN if GPIO.input(button) == ACTIVE else UP for button in BUTTONS}
        self.timer = {button: 0 for button in BUTTONS}
        self.encstate = 0b000000
        self.encvalue = 0
        for button in BUTTONS:
            if button:
                GPIO.add_event_detect(button, GPIO.BOTH, callback=self._button_event)
        for channel in ROT_R, ROT_L:
            if channel:
                GPIO.add_event_detect(channel, GPIO.BOTH, callback=self._encoder_event)
        self.buttoncallback = None

    def _button_event(self, button):
        t = time.time()
        self.timer[button] = t

    def _encoder_event(self, channel):
        for channel in ROT_L, ROT_R:
            self.encstate = (self.encstate << 1) % 64
            self.encstate += 1 if GPIO.input(channel) == ACTIVE else 0
        if self.encstate in (0b111000, 0b011000, 0b011100):
            self.encvalue += 1
        elif self.encstate in (0b110100, 0b100100, 0b101100):
            self.encvalue -= 1

    def update(self):
        # call regularly to update display and poll buttons/encoder
        t = time.time()
        for r, text in enumerate(self.lines):
            if text == "": continue
            towrite = text.strip(PADLEFT)[:COLS]
            for c, newchar, oldchar in zip(range(COLS), towrite, self.written[r]):
                if newchar != oldchar:
                    self.LCD.cursor_pos = r, c
                    self.LCD.write_string(newchar)
            self.written[r] = towrite
            if len(text) > COLS:
                if t - self.lastscroll < SCROLL_TIME: continue
                self.lastscroll = t
                if text[COLS] == PADRIGHT: # end of text, pause a bit
                    self.lines[r] = text[:COLS] + text[COLS + 1:]
                elif text[COLS] == PADLEFT: # wrap back to beginning
                    self.lines[r] = text[COLS:] + text[:COLS] + PADRIGHT * 4
                else: # shift one character
                    self.lines[r] = text[1:] + text[0]
            else:
                self.lines[r] = ""
        event = NULL
        for button in BUTTONS:
            if t - self.timer[button] > BOUNCE_TIME:
                if GPIO.input(button) == ACTIVE:
                    if self.state[button] == UP:
                        self.state[button] = DOWN
                        if button in BTN_SW and self.buttoncallback:
                            self.buttoncallback(BTN_SW.index(button), 1)
                    elif self.state[button] == DOWN and t - self.timer[button] >= HOLD_TIME:
                        self.state[button] = HELD
                        if button in (BTN_R, BTN_ROT): event = SELECT
                        elif button == BTN_L: event = ESCAPE
                        elif button in BTN_SW and not self.buttoncallback: event = ESCAPE
                else:
                    if self.state[button] != UP and button in BTN_SW and self.buttoncallback:
                        self.buttoncallback(BTN_SW.index(button), 0)
                    if self.state[button] == DOWN:
                        if button == BTN_L: event = LEFT
                        elif button == BTN_R: event = RIGHT
                        elif button in BTN_SW and not self.buttoncallback: event = LEFT
                    self.state[button] = UP
        if self.encvalue > 0: event = RIGHT
        elif self.encvalue < 0: event = LEFT
        self.encvalue = 0
        time.sleep(POLL_TIME)
        return event

    def waitfortap(self, t=0):
        # wait until a button is tapped
        # if t>0 wait at most t: seconds
        # return True if button was tapped, else False
        tstop = time.time() + t
        while True:
            if t and time.time() > tstop:
                return False
            if self.update() != NULL:
                return True

    def lcd_clear(self):
        self.LCD.clear()
        self.lines = [""] * ROWS
        self.written = [" " * COLS] * ROWS

    def lcd_write(self, text, row=0, scroll=False, rjust=False, now=False):
        if scroll and len(text) > COLS:
            self.lines[row] = PADLEFT * 4 + text + PADRIGHT * 4
        elif rjust:
            self.lines[row] = text[:COLS].rjust(COLS)
        else:
            self.lines[row] = text[:COLS].ljust(COLS)
        if now: self.update()

    def lcd_blink(self, text, row=0, n=3, rjust=False):
        text = text[:COLS].rjust(COLS) if rjust else text[:COLS].ljust(COLS)
        for _ in range(n):
            self.LCD.cursor_pos = row, 0
            self.LCD.write_string(' ' * COLS)
            time.sleep(BLINK_TIME)
            self.LCD.cursor_pos = row, 0
            self.LCD.write_string(text)
            time.sleep(BLINK_TIME)

    def progresswheel_start(self):
        self.spinning = True
        self.spin = threading.Thread(target=self._progresswheel_spin)
        self.spin.start()
    
    def _progresswheel_spin(self):
        while self.spinning:
            for x in BACKSLASH, '|', '/', '-':
                self.LCD.cursor_pos = ROWS - 1, COLS - 1
                self.LCD.write_string(x)
                time.sleep(BLINK_TIME)

    def progresswheel_stop(self):
        self.spinning = False
        self.spin.join()
        self.LCD.cursor_pos = ROWS - 1, COLS - 1
        self.LCD.write_string(' ')

    def confirm_choice(self, text='', row=1, timeout=MENU_TIMEOUT):
        self.lcd_write(text[:COLS - 1], row=row, now=True)
        c = 1
        while True:
            self.LCD.cursor_pos = row, COLS - 1
            self.LCD.write_string([XMARK, CHECK][c])
            tstop = time.time() + timeout
            while timeout == 0 or time.time() < tstop:
                event = self.update()
                if event in (RIGHT, LEFT):
                    c ^= 1
                    break
                elif event == SELECT:
                    if c: self.lcd_blink(text[:COLS], row=row)
                    return c
                elif event == ESCAPE:
                    return 0
            else:
                return 0

    def choose_opt(self, opts, i=0, row=0, scroll=False, timeout=MENU_TIMEOUT, rjust=False):
        # choose from list of options in :opts
        # start with option :i
        # returns the choice index
        # or -1 if user backs out or time expires
        if timeout == 0:
            opts += (f"{XMARK} cancel", )
        while True:
            self.lcd_write(opts[i], row=row, scroll=scroll, rjust=rjust)
            tstop = time.time() + timeout
            while timeout == 0 or time.time() < tstop:
                event = self.update()
                if event == RIGHT:
                    i = (i + 1) % len(opts)
                    break
                elif event == LEFT:
                    i = (i - 1) % len(opts)
                    break
                elif event == SELECT:
                    if opts[i] == XMARK + " cancel": return -1
                    self.lcd_blink(opts[i], row, rjust=rjust)
                    return i
                elif event == ESCAPE:
                    self.lcd_write('', row)
                    return -1
            else:
                self.lcd_write('', row)
                return -1


    def choose_val(self, val, inc, minval, maxval, fmt=f'>{COLS}', timeout=MENU_TIMEOUT):
        # lets user choose a numeric parameter
        # returns user's choice on timeout
        while True:
            self.lcd_write(format(val, fmt), 1, rjust=True)
            tstop = time.time() + timeout
            while time.time() < tstop:
                event = self.update()
                if event == RIGHT:
                    val = min(val + inc, maxval)
                    break
                elif event == LEFT:
                    val = max(val - inc, minval)
                    break
                elif event == SELECT:
                    self.lcd_blink(format(val, fmt), 1, rjust=True)
                    return val
                elif event == ESCAPE:
                    return None
            else:
                return None

    def char_input(self, text=' ', i=-1, row=1, timeout=MENU_TIMEOUT, charset=INPCHARS):
        # prompts the user to enter some text with initial value :text
        # starting cursor position :i, if negative then from end of string
        if i < 0: i = len(text) + i
        c = charset.find(text[i]) # index in charset
        self.LCD.cursor_mode = 'line'
        while True:
            if self.LCD.cursor_mode == 'line':
                self.lcd_write(text[max(0, i + 1 - COLS):max(COLS, i + 1)], row=row, now=True)
            else:
                self.LCD.write_string(charset[c])
            self.LCD.cursor_pos = row, min(i, COLS - 1)
            tstop = time.time() + timeout
            while time.time() < tstop:
                event = self.update()
                if event == NULL: continue
                if event == RIGHT:
                    if self.LCD.cursor_mode == 'line':
                        i = min(i + 1, len(text))
                        if i == len(text): text += ' '
                        c = charset.find(text[i])
                    else:
                        c = (c + 1) % len(charset)
                        text = text[0:i] + charset[c] + text[i + 1:]
                elif event == LEFT:
                    if self.LCD.cursor_mode == 'line':
                        i = max(i - 1, 0)
                        c = charset.find(text[i])
                    else:
                        c = (c - 1) % len(charset)
                        text = text[0:i] + charset[c] + text[i + 1:]
                elif event == SELECT:
                    self.LCD.cursor_mode = 'line' if self.LCD.cursor_mode == 'blink' else 'blink'
                elif event == ESCAPE:
                    self.LCD.cursor_mode = 'hide'
                break
            else:
                self.LCD.cursor_mode = 'hide'
            if self.LCD.cursor_mode == 'hide':
                if self.confirm_choice(text.strip()[1 - COLS:], row=row):
                    return text.strip()
                else:
                    return ''

    def gpio_set(self, n, state):
        if n < len(PIN_OUT):
            if state == 1:
                GPIO.output(PIN_OUT[n], GPIO.HIGH)
            else:
                GPIO.output(PIN_OUT[n], GPIO.LOW)
