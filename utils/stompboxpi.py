"""
Description: python interface for a raspberry pi with two gpio buttons and a 16x2 character LCD
"""


# adjust timings below as needed/desired
POLL_TIME = 0.01
HOLD_TIME = 1.0
LONG_TIME = 3.0
MENU_TIMEOUT = 5.0
BLINK_TIME = 0.1
SCROLL_TIME = 0.4


COLS, ROWS = 16, 2

import time
import RPLCD, RPi.GPIO as GPIO
from .hw_overlay import *

if ACTIVE_HIGH:
    ACTIVE = GPIO.HIGH
else:
    ACTIVE = GPIO.LOW

UP = 0
DOWN = 1
TAP = 2
HOLD = 3
HELD = 4
LONG = 5
LONGER = 6
CHR_BSP = 0
CHR_ENT = 1
INPCHARS = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.\/" + chr(CHR_BSP) + chr(CHR_ENT)
PRNCHARS = ''' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~''' + chr(CHR_BSP) + chr(CHR_ENT)
BUTTONS = BTN_L, BTN_R

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
        self.LCD.create_char(CHR_BSP,[0,3,5,9,5,3,0,0])
        self.LCD.create_char(CHR_ENT,[0,1,5,9,31,8,4,0])
        self.lcd_clear()
        self.scrolltext = ''

        # set up buttons
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for button in BUTTONS:
            if ACTIVE_HIGH:
                GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            else:
                GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.state = {button: UP for button in BUTTONS}
        self.timer = {button: 0 for button in BUTTONS}

    @property
    def buttons(self):
        return self.state.values()

    @property
    def left(self):
        return self.state[BTN_L]

    @property
    def right(self):
        return self.state[BTN_R]

    def button(self, button):
        return self.state[button]
        
    def update(self):
        time.sleep(POLL_TIME)
        t = time.time()
        for button in BUTTONS:
            if GPIO.input(button) != ACTIVE:
                self.timer[button] = t
                if self.state[button] == DOWN:
                    self.state[button] = TAP
                else:
                    self.state[button] = UP
            else:
                if self.state[button] == UP:
                    self.state[button] = DOWN
                    self.timer[button] = t
                elif self.state[button] == DOWN:
                    if (t - self.timer[button]) >= HOLD_TIME:
                        self.state[button] = HOLD
                elif self.state[button] == HOLD:
                    self.state[button] = HELD
                elif self.state[button] == HELD:
                    if (t - self.timer[button]) >= LONG_TIME:
                        self.state[button] = LONG
                elif self.state[button] == LONG:
                    self.state[button] = LONGER
        if self.scrolltext:
            if (t - self.lastscroll) >= SCROLL_TIME:
                self.lastscroll = t
                self.s += 1
                if 0 < self.s <= len(self.scrolltext) - COLS:
                    self.LCD.cursor_pos = (self.scrollrow, 0)
                    self.LCD.write_string(self.scrolltext[self.s:self.s + COLS])
                elif self.s > len(self.scrolltext) - COLS + 3:
                    self.s = -4
                    self.LCD.cursor_pos = (self.scrollrow, 0)
                    self.LCD.write_string(self.scrolltext[:COLS])

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
            self.update()
            if TAP in self.buttons:
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
            self.lcd_write(text, row)
            time.sleep(BLINK_TIME)
            n -= 1

    def choose_opt(self, opts, row=0, scroll=False, timeout=MENU_TIMEOUT, passlong=False, rjust=False):
        # choose from list of options in :opts
        # returns the choice index
        # or -1 if user backs out or time expires
        i=0
        while True:
            self.lcd_write(opts[i], row=row, scroll=scroll, rjust=rjust)
            tstop = time.time() + timeout
            while True:
                if timeout and time.time() > tstop:
                    self.lcd_write(' ' * COLS, row)
                    return -1
                self.update()
                if self.right == TAP:
                    i = (i + 1) % len(opts)
                    break
                elif self.left == TAP:
                    i = (i - 1) % len(opts)
                    break
                elif self.right == HOLD:
                    self.lcd_blink(opts[i], row, rjust=rjust)
                    return i
                elif self.left == HOLD:
                    self.lcd_write(' ' * COLS, row)
                    return -1
                elif LONG in self.state.values() and passlong:
                    for b in self.state:
                        if self.state[b] == LONG:
                            self.state[b] = HELD
                    return -1

    def choose_val(self, val, inc, minval, maxval, fmt=f'>{COLS}', timeout=MENU_TIMEOUT):
        # lets user choose a numeric parameter
        # returns user's choice on timeout
        while True:
            self.lcd_write(format(val, fmt), 1, rjust=True)
            tstop = time.time() + timeout
            while time.time() < tstop:
                self.update()
                if self.right > DOWN:
                    val = min(val + inc, maxval)
                    break
                elif self.left > DOWN:
                    val = max(val - inc, minval)
                    break
            else:
                return val

    def char_input(self, text='', row=1, timeout=MENU_TIMEOUT, charset=INPCHARS):
        # text input using two buttons
        # text: initial text value
        # tap chooses character, hold left/right to move cursor
        # at end of input, delete or newline can be selected
        # newline returns text, timeout returns empty string
        i = len(text)
        c = len(charset) - 1
        self.lcd_write(text[-COLS:], row=row)
        self.LCD.cursor_mode = 'blink'
        while True:
            if i < len(text):
                c = charset.find(text[i])
            self.LCD.cursor_pos = (row, min(i, COLS - 1))
            if c > -1:
                self.LCD.write_string(charset[c])
                self.LCD.cursor_pos = (row, min(i, COLS - 1))
            tstop = time.time() + timeout
            while time.time() < tstop:
                self.update()
                if self.right == TAP:
                    if i < len(text):
                        c = (c + 1) % (len(charset) - 2)
                        text = text[0:i] + charset[c] + text[i+1:]
                    else:
                        c = (c + 1) % len(charset)
                    break
                elif self.left == TAP:
                    if i < len(text):
                        c = (c - 1) % (len(charset) - 2)
                        text = text[0:i] + charset[c] + text[i+1:]
                    else:
                        c = (c - 1) % len(charset)
                    break
                elif self.right == HOLD and c == len(charset) - 1:
                    self.LCD.cursor_mode = 'hide'
                    self.lcd_blink(text[:COLS], row)
                    return text.strip()
                elif self.right in (HOLD, LONG, LONGER):
                    if self.right != HOLD: time.sleep(BLINK_TIME)
                    if c < len(charset) - 2:
                        text = text[0:i] + charset[c] + text[i + 1:]
                    i = min(i + 1, len(text))
                    if i == len(text):
                        c = len(charset) - 1
                    self.LCD.cursor_pos = (row, 0)
                    self.lcd_write(text[max(0, i - COLS):max(COLS, i)], row=row)
                    break
                elif self.left in (HOLD, LONG, LONGER):
                    if self.left != HOLD: time.sleep(BLINK_TIME)
                    i = max(i - 1, 0)
                    if c == len(charset) - 2:
                        text = text[0:i] + text[i + 1:]
                    self.LCD.cursor_pos = (row, 0)
                    self.lcd_write(text[max(0, i - COLS):max(COLS, i)], row=row)
                    break
            else:
                self.LCD.cursor_mode = 'hide'
                return ''
