import asyncio

import ntptime
from picovector import ANTIALIAS_BEST, PicoVector
from presto import Presto

import config
from src.logger import logger

presto = Presto(full_res=False, ambient_light=False, layers=1)
touch = presto.touch
display = presto.display
rgb = display.create_pen
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_BEST)
shutdown_event_default = asyncio.Event()
shutdown_event_focused = asyncio.Event()
current_view_state = {
    "mode": "default",
    "next_view_class": None,
    "next_view_kwargs": {},
}


def trigger_shutdown(mode, next_view_class=None, **view_kwargs):
    """Signal to exit current view and switch to specified mode

    Args:
        mode: "default" or "focused" - the view mode to transition to
        next_view_class: Optional view class to instantiate when switching
        **view_kwargs: Keyword arguments to pass to the view constructor
    """
    current_view_state["mode"] = mode
    current_view_state["next_view_class"] = next_view_class
    current_view_state["next_view_kwargs"] = view_kwargs
    if mode == "focused":
        shutdown_event_default.set()
    elif mode == "default":
        shutdown_event_focused.set()


async def app_loop(view, shutdown_event):
    """Generic app loop that renders a view until a shutdown event is set"""
    while not shutdown_event.is_set():
        # allow async tasks to run
        # see: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
        await asyncio.sleep(0)
        view.render()
    shutdown_event.clear()


def transition_to_view(view_class, mode, delay_ms=200, **view_kwargs):
    """Transition from current view to a new view

    Args:
        view_class: The view class to instantiate after the delay
        mode: "default" or "focused" - the mode to transition to
        delay_ms: Delay in milliseconds before transition (default: 200)
        **view_kwargs: Keyword arguments to pass to the view constructor
    """
    import time

    # Force display update to ensure pressed state is visible
    presto.update()

    # Delay to show the pressed state
    time.sleep_ms(delay_ms)

    # Signal shutdown with the next view to create and its parameters
    trigger_shutdown(mode, view_class, **view_kwargs)


async def setup_wifi():
    if getattr(config, "DISABLE_WIFI", False):
        return

    if host := getattr(config, "NTP_SERVER", None):
        ntptime.host = host

    while True:
        if presto.wifi.isconnected():
            await asyncio.sleep(15)
            continue

        try:
            await presto.async_connect()
            if presto.wifi.isconnected():
                logger.info(
                    "Networking connection established. IPv4: %s", presto.wifi.ipv4()
                )
                ntptime.settime()
        except Exception as exc:
            logger.error(f"Unable to connect to WiFi. Error: {exc}.")
