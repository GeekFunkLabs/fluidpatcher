"""
Description: model-dependent wiring and behavior
"""

# model 0000 (prototype)
LCD_RS = 24
LCD_EN = 25
LCD_D4 = 8
LCD_D5 = 7
LCD_D6 = 12
LCD_D7 = 16
BTN_L = 5
BTN_R = 6 
ACTIVE_HIGH = 0

# models 0001-0009 (v2 wiring)
# LCD pins on exterior edge of board - easier for homebrew/perfboard builds
LCD_RS = 15
LCD_EN = 23
LCD_D4 = 24
LCD_D5 = 25
LCD_D6 = 8
LCD_D7 = 7
BTN_L = 27
BTN_R = 22
ACTIVE_HIGH = 1

# models 0010-0024
# SquishBox PCB v3
LCD_RS = 4
LCD_EN = 27
LCD_D4 = 9
LCD_D5 = 11
LCD_D6 = 5
LCD_D7 = 6
BTN_L = 2
BTN_R = 3
ACTIVE_HIGH = 0

# models 0025-
# SquishBox PCB v4
LCD_RS = 4
LCD_EN = 17
LCD_D4 = 9
LCD_D5 = 11
LCD_D6 = 5
LCD_D7 = 6
BTN_L = 0
BTN_R = 0
ROT_L = 2
ROT_R = 3
BTN_ROT = 27
BTN_SW = 22
PIN_LED = 10
ACTIVE_HIGH = 0
BUTTONS = BTN_ROT, BTN_SW

# testing
LCD_RS = 4
LCD_EN = 27
LCD_D4 = 9
LCD_D5 = 11
LCD_D6 = 5
LCD_D7 = 6
BTN_L = 0
BTN_R = 0
ROT_L = 8
ROT_R = 25
BTN_ROT = 24
BTN_SW = 3
PIN_LED = 2
BUTTONS = BTN_ROT, BTN_SW
