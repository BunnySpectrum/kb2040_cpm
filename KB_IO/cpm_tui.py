import dataclasses

import byte_stream_py
import ee_point
from KB_IO.ee_point import EePoint


@dataclasses.dataclass
class RenderContext:
    origin: ee_point.EePoint
    active_row: int

class EeComposer:
    def __init__(self, stream: byte_stream_py.ByteStreamPy):
        self._stream = stream

    def move_to(self, point: EePoint):
        self._stream.write_string(f'\x1b[{point.col()};{point.row()}H')

    def move_down(self, rows: int):
        print(f'\x1b[{rows}B', end='')

    def move_left(self, cols: int):
        print(f'\x1b[{cols}D', end='')

    def clear_screen(self):
        print('\x1b[2J', end='')

    def clear_chars(self, length: int):
        if(length > 0):
            return




    def compose_bar(self, is_top: bool, length: int):
        if is_top:
            left_corner = '/'
            right_corner = '\\'
        else:
            left_corner = '\\'
            right_corner = '/'
        print(f'{left_corner}-\x1b[{length-3}b{right_corner}', end='')

if __name__ == '__main__':
    import time
    import random

    tui = EeComposer(width=10, height=10)
    print(tui)
    tui.clear_screen()
    tui.move_to(1,1)
    tui.compose_bar(True, 10)
    points = []
    for _ in range(10):
        x = random.randint(2, 8)
        y = random.randint(2, 8)
        tui.move_to(x,y)
        print(_)
        points.append((x,y))

    tui.move_to(1,10)
    tui.compose_bar(False, 10)
    print('')
    print(points)
