#!/usr/bin/env python3
"""Put a cool splash logo on the LCD
"""

import time

import RPi.GPIO as GPIO

# versions
HW_VERSION = 'v6'
SB_VERSION = '0.8.2'

LCD_RS = 2; LCD_EN = 3; LCD_DATA = 11, 5, 6, 13
if HW_VERSION == 'v4':
    LCD_RS = 4; LCD_EN = 17; LCD_DATA = 9, 11, 5, 6
elif HW_VERSION == 'v3':
    LCD_RS = 4; LCD_EN = 27; LCD_DATA = 9, 11, 5, 6
elif HW_VERSION == 'v2':
    LCD_RS = 15; LCD_EN = 23; LCD_DATA = 24, 25, 8, 7
COLS, ROWS = 16, 2

logobits = [[0, 0, 4, 11, 4, 0, 1, 2], [2, 5, 2, 18, 18, 18, 31, 0],
    [0, 0, 2, 5, 2, 2, 31, 0], [0, 0, 0, 0, 2, 5, 18, 10],
    [2, 10, 22, 10, 2, 2, 2, 1], [0, 31, 23, 23, 23, 18, 18, 31],
    [0, 31, 29, 29, 29, 9, 9, 31], [10, 10, 10, 14, 8, 8, 8, 16]]

def lcd_send(val, reg=0):
    GPIO.output(LCD_RS, reg)
    GPIO.output(LCD_EN, GPIO.LOW)
    for nib in (val >> 4, val):
        for i in range(4):
            GPIO.output(LCD_DATA[i], (nib >> i) & 0x01)
        GPIO.output(LCD_EN, GPIO.HIGH)
        time.sleep(50e-6)
        GPIO.output(LCD_EN, GPIO.LOW)

# set up GPIO, initialize LCD
GPIO.setmode(GPIO.BCM)
for channel in (LCD_RS, LCD_EN, *LCD_DATA):
    GPIO.setup(channel, GPIO.OUT)
for val in (0x33, 0x32, 0x28, 0x0c, 0x06):
    lcd_send(val)

# create custom characters
for loc, bits in enumerate(logobits):
    lcd_send(0x40 | loc << 3)
    for row in bits:
        lcd_send(row, 1)

lcd_send(0x01) # clear LCD
time.sleep(2e-3)
version_str = f"{HW_VERSION}/{SB_VERSION}".rjust(11)
lcd_send(0x80) # cursor to row 0, column 0
for c in " \x00\x01\x02\x03  SquishBox":
    lcd_send(ord(c), 1)
lcd_send(0xc0) # cursor to row 1, column 0
for c in f" \x04\x05\x06\x07{version_str}":
    lcd_send(ord(c), 1)
