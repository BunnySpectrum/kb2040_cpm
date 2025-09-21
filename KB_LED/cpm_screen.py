import adafruit_displayio_ssd1306
from adafruit_display_text import label
import displayio
import i2cdisplaybus
import terminalio

kBorder = 5
class CpmScreen:
    def __init__(self, display_bus: i2cdisplaybus.I2CDisplayBus, width: int, height: int):
        self.display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=width, height=height)
        self.display.root_group = displayio.Group()
        self._width = width
        self._height = height

    def start(self, msg: str):
        color_bitmap = displayio.Bitmap(self._width, self._height, 1)
        color_palette = displayio.Palette(1)
        color_palette[0] = 0xFFFFFF  # White
        bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        self.display.root_group.append(bg_sprite)

        inner_bitmap = displayio.Bitmap(self._width - kBorder * 2, self._height - kBorder * 2, 1)
        inner_palette = displayio.Palette(1)
        inner_palette[0] = 0x000000  # Black
        inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=kBorder, y=kBorder)
        self.display.root_group.append(inner_sprite)

        text_area = label.Label(terminalio.FONT, text=msg, color=0xFFFFFF, x=28, y=self._height // 2 - 1)
        self.display.root_group.append(text_area)
