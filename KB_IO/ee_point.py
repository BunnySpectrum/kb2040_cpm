
class EePoint:
    def __init__(self, col: int, row: int):
        self._col = col
        self._row = row

    def __add__(self, other) -> 'EePoint':
        return EePoint(self._col + other._col, self._row + other._row)

    def row(self) -> int:
        return self._row

    def col(self) -> int:
        return self._col