import math
import time

from picovector import Polygon
from touch import Button

from src.colors import (
    BLACK,
    GRAY_200,
    GRAY_600,
    GRAY_900,
    GREEN_500,
    GREEN_900,
    PURPLE_600,
    WHITE,
)
from src.core import display, presto, transition_to_view, vector
from src.logger import logger
from src.models import ROOMS, get_room

# sizes & spacing
WIDTH, HEIGHT = display.get_bounds()
GAP = 8
TILES = 4
TILE_SIZE = (WIDTH - (GAP * (TILES - 1))) / TILES


class SplashView:
    def render(self):
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.text("Thermostat\nController", 8, HEIGHT // 2 - 24, WIDTH, 4)
        presto.update()
        time.sleep(2)


class FocusedView:
    SAVE_DELAY_MS = 3000

    def __init__(self, room_name="room"):
        display.set_pen(BLACK)
        display.clear()
        presto.update()

        self.room = get_room(room_name)
        if not self.room:
            from src.models import Room
            self.room = Room(room_name, actual_temp=None, desired_temp=20.0)

        self._original_desired_temp = self.room.desired_temp
        self._last_change_time = None
        self._save_pending = False
        self._save_message_shown = False

        self.close_tile = CloseTile(left=WIDTH - TILE_SIZE)

        self.temperature_tile = FocusedTile(
            room=self.room,
            size=2,
            value_size=4,
            initial_value=self.room.desired_temp,
            top=HEIGHT // 2 - size(2) // 2,
            left=WIDTH // 2 - size(2) // 2,
        )

        self.minus_tile = MinusTile(
            top=HEIGHT // 2 - TILE_SIZE // 2,
            focused_view=self,
        )

        self.plus_tile = PlusTile(
            top=HEIGHT // 2 - TILE_SIZE // 2,
            left=WIDTH - TILE_SIZE,
            focused_view=self,
        )

        _mode_top = HEIGHT - int(TILE_SIZE)
        _mode_left = (WIDTH - (int(TILE_SIZE) * 2 + GAP)) // 2
        self.off_tile = ModeTile(
            mode="off",
            focused_view=self,
            top=_mode_top,
            left=_mode_left,
        )
        self.heat_tile = ModeTile(
            mode="heat",
            focused_view=self,
            top=_mode_top,
            left=_mode_left + int(TILE_SIZE) + GAP,
        )

        for component in self.__dict__.values():
            if isinstance(component, Component):
                component.draw()

    def adjust_temperature(self, adjustment):
        self.room.adjust_desired_temp(adjustment)
        self.temperature_tile.set_state(self.room.desired_temp)
        self._last_change_time = time.ticks_ms()
        self._save_pending = True
        self._save_message_shown = False

    def set_mode(self, mode):
        self.room.hvac_mode = mode
        from src import ha_service
        svc = ha_service.get()
        if svc:
            svc.set_hvac_mode(self.room.name, mode)

    def _check_save_pending(self):
        if not self._save_pending:
            return
        elapsed = time.ticks_diff(time.ticks_ms(), self._last_change_time)
        if elapsed >= self.SAVE_DELAY_MS:
            self._save_temperature()

    def _save_temperature(self):
        self._save_pending = False
        logger.info("Saving %s: desired_temp=%s", self.room.name, self.room.desired_temp)

        from src import ha_service
        svc = ha_service.get()
        if svc:
            svc.set_temperature(self.room.name, self.room.desired_temp)

        self._show_save_message()

    def _show_save_message(self):
        display.set_pen(GREEN_500)
        display.text("Saved", WIDTH // 2 - 30, HEIGHT - 30, WIDTH, 2)
        presto.update()
        time.sleep(2)
        display.set_pen(BLACK)
        display.rectangle(0, HEIGHT - 40, WIDTH, 40)
        presto.update()
        self._save_message_shown = True

    def render(self):
        self._check_save_pending()
        self.close_tile.draw()
        self.temperature_tile.draw()
        self.minus_tile.draw()
        self.plus_tile.draw()
        self.off_tile.draw()
        self.heat_tile.draw()


class DefaultView:
    def __init__(self):
        display.set_pen(BLACK)
        display.clear()
        presto.update()

        self._room_tiles = []
        self._known_rooms = frozenset()
        self._last_connect_status = None
        self._build_tiles()

    def _build_tiles(self):
        self._room_tiles = []
        self._known_rooms = frozenset(ROOMS.keys())
        self._last_connect_status = None

        rooms = list(ROOMS.values())[:TILES * 2]
        if not rooms:
            return

        display.set_pen(BLACK)
        display.clear()
        presto.update()

        for i, room in enumerate(rooms):
            col = i % TILES
            row = i // TILES
            left = col * (int(TILE_SIZE) + GAP)
            top = row * (int(TILE_SIZE) + GAP)
            TileClass = ValueTile if room.desired_temp is None else TouchTile
            tile = TileClass(
                description=shorten_name(room.name),
                initial_value=room.actual_temp_str,
                left=left,
                top=top,
                room_name=room.name,
                room=room,
            )
            self._room_tiles.append((room, tile))

        for _, tile in self._room_tiles:
            tile.draw()

    def _draw_connecting(self):
        wifi_ok = presto.wifi.isconnected()
        status = "WIFI: OK" if wifi_ok else "WIFI: PENDING"
        if status == self._last_connect_status:
            return
        self._last_connect_status = status
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE if wifi_ok else GRAY_600)
        display.text(status, 8, HEIGHT // 2 - 8, WIDTH, 3)
        presto.update()

    def render(self):
        current_rooms = frozenset(ROOMS.keys())
        if current_rooms != self._known_rooms:
            self._build_tiles()

        if not self._room_tiles:
            self._draw_connecting()
            return

        for room, tile in self._room_tiles:
            new_val = room.actual_temp_str
            if isinstance(tile, TouchableTile):
                tile._set_state(new_val)
                tile.draw()
            elif tile._value != new_val:
                tile.set_state(new_val)


def size(tiles):
    return (TILE_SIZE * tiles) + (GAP * (tiles - 1))


def shorten_name(name, max_len=8):
    name = name.replace("_", " ")
    if len(name) <= max_len:
        return name
    words = name.split(" ")
    if len(words) == 1:
        return name[:max_len - 1] + "."
    first = words[0][:2] + "."
    remaining = max_len - len(first) - 1
    return first + " " + words[1][:remaining]


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

    def _increment_state(self, *args, **kwargs):
        raise NotImplementedError()

    def draw(self):
        self._draw()
        self._flush()

    def set_state(self, *args, **kwargs):
        self._set_state(*args, **kwargs)
        self.draw()

    def increment_state(self, *args, **kwargs):
        self._increment_state(*args, **kwargs)
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
        tile_size = int(kwargs.pop("size", 1))
        self.width = size(tile_size)
        self.height = size(tile_size)
        self.size = tile_size
        self._bg = None

    def _draw_bg(self, color=GRAY_900):
        if self._bg is None:
            bg = Polygon()
            bg.rectangle(self.left, self.top, self.width, self.height)
            self._bg = bg
        display.set_pen(color)
        vector.draw(self._bg)


class BaseTile(Tile):
    bg_color = GRAY_900
    value_color = GRAY_200
    description_color = GRAY_600

    def __init__(self, description: str | None = None, initial_value=None, **kwargs):
        self._value_offset_x = int(kwargs.pop("value_offset_x", 0))
        self._value_offset_y = int(kwargs.pop("value_offset_y", 0))

        super().__init__(**kwargs)
        self.value_size = int(kwargs.pop("value_size", 3))
        self._description = description
        self._value = None
        self._value_pos = (
            self.left + GAP + self._value_offset_x,
            self.top + GAP + 6 + self._value_offset_y,
        )
        self._description_pos = self.left + GAP, self.bottom - GAP - 10
        self._set_state(initial_value)

    def _set_state(self, value):
        self._value = value

    def _increment_state(self, value):
        if isinstance(self._value, (int, float)):
            self._value = math.floor((self._value + value) * 10) / 10

    def _draw_value(self):
        _value = str(self._value) if self._value is not None else "-"
        display.set_pen(self.value_color)
        display.text(_value, *self._value_pos, WIDTH, self.value_size)

    def _draw_description(self):
        if self._description is not None:
            display.set_pen(self.description_color)
            display.text(self._description, *self._description_pos, WIDTH, 1)

    def _draw(self):
        self._draw_bg(self.bg_color)
        self._draw_value()
        self._draw_description()


class TouchableTile(BaseTile):
    pressed_bg_color = GREEN_900
    pressed_value_color = GREEN_500

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._button = Button(self.left, self.top, self.width, self.height)
        self._is_pressed = False

    def _handle_press(self):
        pass

    def _draw(self):
        is_pressed = self._button.is_pressed()

        self.bg_color = self.pressed_bg_color if is_pressed else GRAY_900
        self.value_color = self.pressed_value_color if is_pressed else GRAY_200

        super()._draw()

        if is_pressed and self._is_pressed:
            self._handle_press()

        self._is_pressed = is_pressed


class ValueTile(BaseTile):
    """Static read-only tile"""
    pass


class FocusedTile(BaseTile):
    """Centre tile for the focused room view — actual temp, desired temp, room name."""

    def __init__(self, room=None, **kwargs):
        super().__init__(**kwargs)
        self._room = room

    def _draw(self):
        self._draw_bg(self.bg_color)
        room = self._room
        x = self.left + GAP
        y0 = self.top + GAP
        is_heating = room and getattr(room, "hvac_action", None) == "heating"

        actual = f"{room.actual_temp:.1f}" if room and room.actual_temp is not None else "-"
        display.set_pen(self.description_color)
        display.text(f"courante: {actual}", x, y0, WIDTH, 1)

        display.text("desiree:", x, y0 + 22, WIDTH, 1)

        desired = f"{self._value:.1f}" if isinstance(self._value, float) else (str(self._value) if self._value is not None else "-")
        display.set_pen(PURPLE_600 if is_heating else self.value_color)
        display.text(desired, x, y0 + 36, WIDTH, self.value_size)

        display.set_pen(self.description_color)
        display.text(room.name.replace("_", " ") if room else "", x, self.bottom - GAP - 10, WIDTH, 1)


class ModeTile(TouchableTile):
    """Button tile that sets the HVAC mode (heat / off)."""

    def __init__(self, mode, focused_view=None, **kwargs):
        kwargs.setdefault("value_offset_y", 6)
        kwargs.setdefault("value_size", 2)
        super().__init__(**kwargs)
        self._mode = mode
        self._focused_view = focused_view
        self._value = "on" if mode == "heat" else mode

    def _draw(self):
        is_pressed = self._button.is_pressed()
        room = self._focused_view.room if self._focused_view else None
        is_active = room and getattr(room, "hvac_mode", None) == self._mode

        if is_pressed:
            self.bg_color = self.pressed_bg_color
            self.value_color = self.pressed_value_color
        elif is_active:
            self.bg_color = GREEN_900
            self.value_color = GREEN_500
        else:
            self.bg_color = GRAY_900
            self.value_color = GRAY_600

        BaseTile._draw(self)

        if is_pressed and self._is_pressed:
            self._handle_press()
        self._is_pressed = is_pressed

    def _draw_value(self):
        _text = str(self._value) if self._value is not None else "-"
        text_width = display.measure_text(_text, self.value_size)
        x = self.left + (int(self.width) - text_width) // 2
        _, y = self._value_pos
        display.set_pen(self.value_color)
        display.text(_text, x, y, WIDTH, self.value_size)

    def _handle_press(self):
        logger.info(f"Mode: {self._mode}")
        if self._focused_view:
            self._focused_view.set_mode(self._mode)


class TouchTile(TouchableTile):
    def __init__(self, room=None, room_name=None, **kwargs):
        super().__init__(**kwargs)
        self._room = room
        self._room_name = room_name or self._description

    def _draw(self):
        is_pressed = self._button.is_pressed()
        is_heating = self._room and getattr(self._room, "hvac_action", None) == "heating"

        self.bg_color = self.pressed_bg_color if is_pressed else GRAY_900
        if is_pressed:
            self.value_color = self.pressed_value_color
        elif is_heating:
            self.value_color = PURPLE_600
        else:
            self.value_color = GRAY_200

        BaseTile._draw(self)

        if is_pressed and self._is_pressed:
            self._handle_press()
        self._is_pressed = is_pressed

    def _handle_press(self):
        logger.info(f"Pressed {self._room_name}")
        transition_to_view(
            FocusedView,
            "focused",
            room_name=self._room_name,
        )


class AdjustTile(TouchableTile):
    def __init__(self, focused_view=None, symbol="+", adjustment=0.1, **kwargs):
        super().__init__(**kwargs)
        self._focused_view = focused_view
        self._value = symbol
        self._adjustment = adjustment

    def _handle_press(self):
        logger.info(f"{self.__class__.__name__} pressed")
        if self._focused_view:
            self._focused_view.adjust_temperature(self._adjustment)
            time.sleep_ms(50)


class PlusTile(AdjustTile):
    VALUE_OFFSET_X = 14
    VALUE_OFFSET_Y = 2

    def __init__(self, **kwargs):
        kwargs.setdefault("value_offset_x", self.VALUE_OFFSET_X)
        kwargs.setdefault("value_offset_y", self.VALUE_OFFSET_Y)
        super().__init__(symbol="+", adjustment=0.1, **kwargs)


class MinusTile(AdjustTile):
    VALUE_OFFSET_X = 14
    VALUE_OFFSET_Y = 2

    def __init__(self, **kwargs):
        kwargs.setdefault("value_offset_x", self.VALUE_OFFSET_X)
        kwargs.setdefault("value_offset_y", self.VALUE_OFFSET_Y)
        super().__init__(symbol="-", adjustment=-0.1, **kwargs)


class CloseTile(TouchableTile):
    VALUE_OFFSET_X = 14
    VALUE_OFFSET_Y = 2

    def __init__(self, **kwargs):
        kwargs.setdefault("value_offset_x", self.VALUE_OFFSET_X)
        kwargs.setdefault("value_offset_y", self.VALUE_OFFSET_Y)
        super().__init__(**kwargs)
        self._value = "x"

    def _handle_press(self):
        logger.info("Close pressed")
        transition_to_view(DefaultView, "default")
