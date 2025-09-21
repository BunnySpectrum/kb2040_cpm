import board
import busio
import displayio
import i2cdisplaybus
import neopixel
import time
import supervisor

import tlc5940
import cpm_screen

supervisor.runtime.autoreload = False
displayio.release_displays()

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.fill((0, 0, 128))

i2c = busio.I2C(board.D7, board.D6)
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3D)

spi = busio.SPI(board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# Screen
kWidth = 128
kHeight = 64
screen = cpm_screen.CpmScreen(display_bus=display_bus, width=kWidth, height=kHeight)
screen.start("TLC5940")

# LED driver
led_driver = tlc5940.TLC5940(spi,
                             vprg_pin=board.D9,
                             blank_pin=board.D8,
                             gsclk_pin=board.D5,
                             xlat_pin = board.D10)

while True:
    for led in range(16):
        for shift in range(11):
            led_driver.set_gs_led_data(led, 0xFFF >>shift)
            led_driver.program()
            time.sleep(0.1)
        else:
            led_driver.set_gs_led_data(led, 0xFFF)