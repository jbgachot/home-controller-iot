
import math
import asyncio
import time

from src.core import display
from src.core import presto
from src.core import vector
from src.core import presto
from src.core import rgb
from src.core import trigger_shutdown
from src.core import app_loop
from src.buzzer import play_melody
from src.logger import logger

from picovector import Polygon
from touch import Button


# sizes & spacing
WIDTH, HEIGHT = display.get_bounds()
GAP = 8
TILES = 4
TILE_SIZE = (WIDTH - (GAP * (TILES - 1))) / TILES

# colors
WHITE = rgb(255, 255, 255)
BLACK = rgb(0, 0, 0)

GRAY_950 = rgb(10, 10, 10)
GRAY_900 = rgb(23, 23, 23)
GRAY_800 = rgb(38, 38, 38)
GRAY_700 = rgb(64, 64, 64)
GRAY_600 = rgb(82, 82, 82)
GRAY_500 = rgb(115, 115, 115)
GRAY_400 = rgb(163, 163, 163)
GRAY_300 = rgb(212, 212, 212)
GRAY_200 = rgb(229, 229, 229)
GRAY_100 = rgb(245, 245, 245)
GRAY_50 = rgb(250, 250, 250)

GREEN_400 = rgb(74, 222, 128)
GREEN_500 = rgb(34, 197, 94)
GREEN_600 = rgb(22, 163, 74)
GREEN_800 = rgb(22, 101, 52)
GREEN_900 = rgb(20, 83, 45)

ROSE_400 = rgb(248, 113, 113)
ROSE_600 = rgb(225, 29, 72)
ROSE_800 = rgb(159, 18, 57)
ROSE_900 = rgb(127, 29, 29)

SKY_400 = rgb(56, 189, 248)
SKY_600 = rgb(2, 132, 199)
SKY_800 = rgb(7, 89, 133)
SKY_900 = rgb(12, 74, 110)

PURPLE_600 = rgb(147, 51, 234)

AMBER_400 = rgb(251, 191, 36)
AMBER_500 = rgb(234, 179, 8)
AMBER_600 = rgb(217, 119, 6)
AMBER_800 = rgb(146, 64, 14)
AMBER_900 = rgb(120, 53, 15)

class SplashView:
    def render(self):
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.text("Thermostat\nController", 8, HEIGHT // 2 - 24, WIDTH, 4)
        presto.update()

class FocusedView:
    def __init__(self):
        display.set_pen(BLACK)
        display.clear()
        presto.update()

        TouchTile(
            description="moins",
            initial_value="-",
            top=HEIGHT // 2 - TILE_SIZE // 2,
        ).draw()

        ValueTile(
            description="chien",
            initial_value="18°",
            top=HEIGHT // 2 - TILE_SIZE // 2,
            left=WIDTH // 2 - TILE_SIZE // 2,
        ).draw()

        TouchTile(
            description="plus",
            initial_value="+",
            top=HEIGHT // 2 - TILE_SIZE // 2,
            left=WIDTH - TILE_SIZE,
        ).draw()

    def render(self):
        # Tiles with visible interactivity,
        # needs to be drawn in every frame.
        pass

class DefaultView:
    def __init__(self):
        display.set_pen(BLACK)
        display.clear()
        presto.update()

        self.meteo_tile = ValueTile(
            description="meteo",
            initial_value="4°",
        )

        self.salon_tile = TouchTile(
            description="salon",
            initial_value="18°",
            left=self.meteo_tile.right + GAP,
        )

        self.chien_tile = TouchTile(
            description="chien",
            initial_value="19°",
            left=self.salon_tile.right + GAP,
        )

        self.maya_tile = TouchTile(
            description="maya",
            initial_value="20°",
            left=self.chien_tile.right + GAP,
        ) 

        # initialize all tiles
        for component in self.__dict__.values():
            if isinstance(component, Component):
                component.draw()

    def render(self):
        # Tiles with visible interactivity,
        # needs to be drawn in every frame.
        self.salon_tile.draw()
        self.chien_tile.draw()
        self.maya_tile.draw()

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

class ValueTile(Tile):
    value_size = 3

    def __init__(self, description: str | None, initial_value=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._value = None
        self._scale = None
        self._set_state(initial_value)
        self._value_pos = self.left + GAP, self.top + GAP + 6
        self._description_pos = self.left + GAP, self.bottom - GAP - 10

    def _create_scale(self, value):
        return GRAY_900, GRAY_200, GRAY_600

    def _set_state(self, value):
        self._value = value
        self._scale = self._create_scale(value)

    def _draw_value(self, value_color):
        _value = str(self._value) if self._value is not None else "-"
        display.set_pen(value_color)
        display.text(_value, *self._value_pos, WIDTH, self.value_size)

    def _draw_description(self, description_color):
        if self._description is not None:
            display.set_pen(description_color)
            display.text(self._description, *self._description_pos, WIDTH, 1)

    def _draw(self):
        bg_color, value_color, description_color = self._scale
        self._draw_bg(bg_color)
        self._draw_value(value_color)
        self._draw_description(description_color)

class TouchTile(Tile):
    value_size = 3

    def __init__(self, description: str | None, initial_value=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._value = None
        self._scale = None
        self._button = None
        self._is_pressed = False
        self._set_state(initial_value)
        self._value_pos = self.left + GAP, self.top + GAP + 6
        self._description_pos = self.left + GAP, self.bottom - GAP - 10

        self._button = Button(self.left, self.top, self.width, self.height)

    def _create_scale(self, value):
        return GRAY_900, GRAY_200, GRAY_600

    def _set_state(self, value):
        self._value = value
        self._scale = self._create_scale(value)

    def _draw_value(self, value_color):
        _value = str(self._value) if self._value is not None else "-"
        display.set_pen(value_color)
        display.text(_value, *self._value_pos, WIDTH, self.value_size)

    def _draw_description(self, description_color):
        if self._description is not None:
            display.set_pen(description_color)
            display.text(self._description, *self._description_pos, WIDTH, 1)

    def _draw(self):
        is_pressed = self._button.is_pressed()
        
        bg_color, value_color, description_color = self._scale
        bg_color = GREEN_900 if is_pressed else bg_color
        self._draw_bg(bg_color)
        value_color = GREEN_500 if is_pressed else value_color
        self._draw_value(value_color)
        self._draw_description(description_color)

        if is_pressed and self._is_pressed:
            logger.info(f"Pressed {self._description}")
            asyncio.create_task(play_melody())
            time.sleep_ms(100)
            asyncio.run(app_loop(FocusedView()))
            trigger_shutdown()
        
        # wait for one last iteration
        self._is_pressed = is_pressed