import asyncio
import config
import ntptime

from presto import Presto

from src.log import logger

presto = Presto(full_res=False, ambient_light=False, layers=1)
display = presto.display
rgb = display.create_pen

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
