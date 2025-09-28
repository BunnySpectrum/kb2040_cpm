import board
import busio
import neopixel
import time
import supervisor
import random

import cpm_tui

supervisor.runtime.autoreload = False

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.fill((128, 0, 128))

i2c = busio.I2C(board.D7, board.D6)
spi = busio.SPI(board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# Screen
kWidth = 80
kHeight = 30
tui = cpm_tui.CpmTui(width=kWidth, height=kHeight)


while True:
    tui.clear_screen()
    tui.move_to(1,1)
    tui.compose_bar(True, kWidth)
    points = []
    for _ in range(10):
        x = random.randint(2, kWidth-2)
        y = random.randint(2, kHeight-2)
        tui.move_to(x,y)
        print(_)
        points.append((x,y))
        time.sleep(1)

    tui.move_to(1,kHeight)
    tui.compose_bar(False, kWidth)
    print('')
    print(points)
    time.sleep(5)