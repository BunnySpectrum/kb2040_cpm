from adafruit_bus_device import spi_device
import digitalio
import busio
import pwmio

try:
    import typing
    from adafruit_blinka.microcontroller.generic_agnostic_board import pin
except ImportError:
    pass

def gs_data_to_bytes(data):
    if len(data) != 16:
        raise ValueError("Data must be 16 bytes long")

    # each input is 12b of data
    result = bytearray([0]*24)
    index = 0
    room = 8

    for value in data:
        if room == 8:
            result[index] |= (value >> 4)
            index += 1
            result [index] |= (value & 0x0F) << 4
            room = 4
        else:
            result[index] |= value >> 8
            index += 1
            result[index] |= (value & 0xFF)
            index += 1
            room = 8

    return result

def dc_data_to_bytes(data):
    if len(data) != 16:
        raise ValueError("Data must be 16 bytes long")

    result = bytearray([0]*12)
    index = 0
    room = 8
    for value in data:
        if room >= 6:
            result[index] |= (value << (room - 6))&0xFF
            room -= 6
        else:
            result[index] |= value >> (6-room)
            index += 1
            result[index] |= (value << (room+2))&0xFF
            room = 8-(6-room)

        if room == 0:
            room = 8
            index += 1

    return result

class TLC5940:
    def __init__(
        self,
        spi: busio.SPI,
        vprg_pin: pin.Pin,
        blank_pin: pin.Pin,
        gsclk_pin: pin.Pin,
        xlat_pin: pin.Pin,
        baudrate: int = 2000000,
    ) -> None:
        self._spi = spi
        self._device = spi_device.SPIDevice(spi=self._spi, baudrate=baudrate, polarity=0, phase=0)
        self._blank_freq = 255
        self._gsclk_freq = self._blank_freq*4096

        self._vprg = digitalio.DigitalInOut(vprg_pin)
        self._vprg.direction = digitalio.Direction.OUTPUT

        self._blank = pwmio.PWMOut(blank_pin,
                                   frequency=self._blank_freq,
                                   duty_cycle=1)
        self._gsclk = pwmio.PWMOut(gsclk_pin,
                                   frequency=self._gsclk_freq,
                                   duty_cycle=2**15)

        self._xlat = digitalio.DigitalInOut(xlat_pin)
        self._xlat.direction = digitalio.Direction.OUTPUT
        self._xlat.value = False

        self._gs_led_data = [0xFFF] * 16
        self._dc_led_data = 16 * [0b000111]

    def set_gs_led_data(self, index: int, value: int):
        self._gs_led_data[index] = value

    def program(self):
        gs_data = gs_data_to_bytes(self._gs_led_data)
        dc_data = dc_data_to_bytes(self._dc_led_data)

        self._vprg.value = False # GS mode
        with self._device:
            self._spi.write(gs_data)

        # pulse high
        self._xlat.value = True
        self._xlat.value = False

        self._vprg.value = True # DC mode
        # need 96 bits (12 bytes)
        # dc_led_data = 4*[0b011111] + 4*[0b001111] + 4*[0b000111] + 4*[0b000011]
        with self._device:
            self._spi.write(dc_data)

        # pulse high
        self._xlat.value = True
        self._xlat.value = False

if __name__ == "__main__":
    import board
    import time

    spi = busio.SPI(board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    led_driver = TLC5940(spi,
                                 vprg_pin=board.D9,
                                 blank_pin=board.D8,
                                 gsclk_pin=board.D5,
                                 xlat_pin=board.D10)
    for led in range(16):
        for shift in range(11):
            led_driver.set_gs_led_data(led, 0xFFF >>shift)
            led_driver.program()
            time.sleep(0.1)
        else:
            led_driver.set_gs_led_data(led, 0xFFF)
