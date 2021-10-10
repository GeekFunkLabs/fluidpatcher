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

import time
import RPLCD, RPi.GPIO as GPIO

COLS, ROWS = 16, 2
ACTIVE_HIGH = 0
BTN_R = 3
BTN_L = 2
ROT_BTN = 24
ROT_L = 8
ROT_R = 25
LCD_RS = 4
LCD_EN = 27
LCD_D4 = 9
LCD_D5 = 11
LCD_D6 = 5
LCD_D7 = 6
try:
    from .hw_overlay import *
except ModuleNotFoundError:
    pass
if ACTIVE_HIGH:
    ACTIVE = GPIO.HIGH
else:
    ACTIVE = GPIO.LOW
BUTTONS = BTN_L, BTN_R, ROT_BTN

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

CHR_NO = 0
CHR_YES = 1
CHR_BSP = 2
CHR_NO_BITS = (
0b00000,
0b11011,
0b01110,
0b00100,
0b01110,
0b11011,
0b00000,
0b00000)
CHR_YES_BITS = (
0b00000,
0b00001,
0b00011,
0b10110,
0b11100,
0b01000,
0b00000,
0b00000)
INPCHARS = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.\/"
PRNCHARS = ''' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'''

class StompBox():

    def __init__(self):
    
        # initialize LCD
        self.LCD = RPLCD.CharLCD(pin_rs=LCD_RS,
                            pin_e=LCD_EN,
                            pin_rw=None,
                            pins_data=[LCD_D4, LCD_D5, LCD_D6, LCD_D7],
                            numbering_mode=GPIO.BCM,
                            cols=COLS, rows=ROWS,
                            compat_mode=True)
        self.LCD.create_char(CHR_NO, CHR_NO_BITS)
        self.LCD.create_char(CHR_YES, CHR_YES_BITS)
        self.lcd_clear()
        self.scrolltext = ''

        # set up buttons
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for button in (*BUTTONS, ROT_R, ROT_L):
            if ACTIVE_HIGH:
                GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            else:
                GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.state = {button: DOWN if GPIO.input(button) == ACTIVE else UP for button in BUTTONS}
        self.timer = {button: 0 for button in BUTTONS}
        self.encstate = 0b00000000
        self.encvalue = 0
        for button in BUTTONS:
            GPIO.add_event_detect(button, GPIO.BOTH, callback=self.button_event)
        for channel in ROT_R, ROT_L:
            GPIO.add_event_detect(channel, GPIO.BOTH, callback=self.encoder_event)

    def button_event(self, button):
        t = time.time()
        self.timer[button] = t

    def encoder_event(self, channel):
        for channel in ROT_L, ROT_R:
            self.encstate = (self.encstate << 1) % 256
            self.encstate += 1 if GPIO.input(channel) == ACTIVE else 0
        if self.encstate == 0b00011110:
            self.encvalue += 1
        elif self.encstate == 0b00101101:
            self.encvalue -= 1

    def update(self):
        time.sleep(POLL_TIME)
        t = time.time()
        event = NULL
        for button in BUTTONS:
            if t - self.timer[button] > BOUNCE_TIME:
                if GPIO.input(button) == ACTIVE:
                    if self.state[button] == UP:
                        self.state[button] = DOWN
                    elif self.state[button] == DOWN and t - self.timer[button] >= HOLD_TIME:
                            if button == BTN_R: event = SELECT
                            if button in (BTN_L, ROT_BTN): event = ESCAPE
                            self.state[button] = HELD
                else:
                    if self.state[button] == DOWN:
                        if button == BTN_L: event = LEFT
                        elif button == BTN_R: event = RIGHT
                        elif button == ROT_BTN: event = SELECT
                    self.state[button] = UP
        if self.encvalue > 0:
            event = RIGHT
            self.encvalue -= 1
        elif self.encvalue < 0:
            event = LEFT
            self.encvalue += 1
        if self.scrolltext:
            if t - self.lastscroll >= SCROLL_TIME:
                self.lastscroll = t
                self.s += 1
                if 0 < self.s <= len(self.scrolltext) - COLS:
                    self.LCD.cursor_pos = (self.scrollrow, 0)
                    self.LCD.write_string(self.scrolltext[self.s:self.s + COLS])
                elif self.s > len(self.scrolltext) - COLS + 3:
                    self.s = -4
                    self.LCD.cursor_pos = (self.scrollrow, 0)
                    self.LCD.write_string(self.scrolltext[:COLS])
        return event

    def waitforrelease(self, tmin=0):
        # wait for all buttons to be released and at least :tmin seconds
        tmin = time.time() + tmin
        while True:
            self.update()
            if time.time() >= tmin:
                if all(s == UP for s in self.state.values()):
                    break

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
        self.scrolltext = ''

    def lcd_write(self, text, row=0, scroll=False, rjust=False):
        if scroll and len(text) > COLS:
            self.scrolltext = text
            self.scrollrow = row
            self.s = -4
            self.lastscroll = time.time()
            self.LCD.cursor_pos = (row, 0)
            self.LCD.write_string(self.scrolltext[:COLS])
        else:
            self.scrolltext = ''
            self.LCD.cursor_pos = (row, 0)
            if rjust:
                self.LCD.write_string(text[:COLS].rjust(COLS))
            else:
                self.LCD.write_string(text[:COLS].ljust(COLS))

    def lcd_blink(self, text, row=0, n=3, rjust=False):
        while n != 0:
            self.lcd_write(' ' * len(text), row, rjust=rjust)
            time.sleep(BLINK_TIME)
            self.lcd_write(text, row, rjust=rjust)
            time.sleep(BLINK_TIME)
            n -= 1

    def confirm_choice(self, text='', row=1, timeout=MENU_TIMEOUT):
        self.lcd_write(text[:COLS - 1], row=row)
        c = 1
        while True:
            self.LCD.cursor_pos = row, COLS - 1
            self.LCD.write_string([chr(CHR_NO), chr(CHR_YES)][c])
            tstop = time.time() + timeout
            while time.time() < tstop:
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
        # returns the choice index
        # or -1 if user backs out or time expires
        while True:
            self.lcd_write(opts[i], row=row, scroll=scroll, rjust=rjust)
            tstop = time.time() + timeout
            while True:
                if timeout and time.time() > tstop:
                    self.lcd_write(' ' * COLS, row)
                    return -1
                event = self.update()
                if event == RIGHT:
                    i = (i + 1) % len(opts)
                    break
                elif event == LEFT:
                    i = (i - 1) % len(opts)
                    break
                elif event == SELECT:
                    self.lcd_blink(opts[i], row, rjust=rjust)
                    return i
                elif event == ESCAPE:
                    self.lcd_write(' ' * COLS, row)
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

    def char_input(self, text='', i=-1, row=1, timeout=MENU_TIMEOUT, charset=INPCHARS):
        # text: initial text value
        if i < 0: i = len(text) + i
        c = charset.find(text[i]) # index in charset
        self.LCD.cursor_mode = 'line'
        while True:
            if self.LCD.cursor_mode == 'line':
                self.lcd_write(text[max(0, i - COLS):max(COLS, i)], row=row)
            else:
                self.LCD.write_string(charset[c])
            self.LCD.cursor_pos = (row, min(i, COLS - 1))
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
                return ''
            if self.LCD.cursor_mode == 'hide':
                if self.confirm_choice(text.strip()[1 - COLS:], row=row):
                    return text.strip()
                else:
                    return ''
