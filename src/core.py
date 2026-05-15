import asyncio
import config
import ntptime

from picovector import ANTIALIAS_BEST, PicoVector

from presto import Presto
from src.logger import logger

presto = Presto(full_res=False, ambient_light=False, layers=1)
touch = presto.touch
display = presto.display
rgb = display.create_pen
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_BEST)
shutdown_event_default = asyncio.Event()
shutdown_event_focused = asyncio.Event()

def trigger_shutdown_default():
    shutdown_event_default.set()
    while shutdown_event_default.is_set():
        pass

async def app_loop_default(view):
    while not shutdown_event_default.is_set():
        # allow async tasks to run
        # see: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
        await asyncio.sleep(0)
        view.render()
    shutdown_event_default.clear()

def trigger_shutdown_focused():
    shutdown_event_focused.set()
    while shutdown_event_focused.is_set():
        pass

async def app_loop_focused(view):
    while not shutdown_event_focused.is_set():
        # allow async tasks to run
        # see: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
        await asyncio.sleep(0)
        view.render()
    shutdown_event_focused.clear()

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
                logger.info("Networking connection established. IPv4: %s", presto.wifi.ipv4())
                ntptime.settime()
        except Exception as exc:
            logger.error(f"Unable to connect to WiFi. Error: {exc}.")
