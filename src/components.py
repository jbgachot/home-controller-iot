import math

from picovector import Polygon

from src.colors import GRAY_900
from src.core import display, presto, vector

# sizes & spacing
WIDTH, HEIGHT = display.get_bounds()
GAP = 8
TILES = 4
TILE_SIZE = (WIDTH - (GAP * (TILES - 1))) / TILES


def size(tiles):
    return (TILE_SIZE * tiles) + (GAP * (tiles - 1))

class Component:
    def __init__(self, **kwargs):
        self.left = int(kwargs.pop("left", kwargs.pop("x", 0)))
        self.top = int(kwargs.pop("top", kwargs.pop("y", 0)))

    def _flush(self):
        x, y = math.floor(self.left), math.ceil(self.top)
        w, h = math.floor(self.width), math.ceil(self.height)
        presto.partial_update(x, y, w, h)

    def _draw(self):
        raise NotImplementedError()

    def _set_state(self, *args, **kwargs):
        raise NotImplementedError()

    def draw(self):
        self._draw()
        self._flush()

    def set_state(self, *args, **kwargs):
        self._set_state(*args, **kwargs)
        self.draw()

    @property
    def right(self):
        return int(self.left + self.width)

    @property
    def bottom(self):
        return int(self.top + self.height)

class Tile(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bg = None
        self.width = size(1)
        self.height = size(1)

    def _draw_bg(self, color=GRAY_900):
        if self._bg is None:
            bg = Polygon()
            bg.rectangle(self.left, self.top, self.width, self.height)
            self._bg = bg
        display.set_pen(color)
        vector.draw(self._bg)