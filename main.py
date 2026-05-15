import asyncio

import config
from src.core import (
    app_loop,
    current_view_state,
    presto,
    setup_wifi,
    shutdown_event_default,
    shutdown_event_focused,
)
from src.logger import logger
from src.views import DefaultView, SplashView


async def ha_sync_task():
    """Background task: connects to Home Assistant and keeps room states in sync"""
    if getattr(config, "DISABLE_WIFI", False):
        return

    import secrets

    from src import ha_service

    # Wait until WiFi is up
    while not presto.wifi.isconnected():
        await asyncio.sleep(5)

    svc = ha_service.init(secrets.HA_URL, secrets.HA_TOKEN)
    if not svc.connect():
        logger.error("Failed to connect to Home Assistant")
        return

    svc.discover_thermostats()
    svc.sync_weather_forecast()

    interval_s = getattr(config, "HA_SYNC_INTERVAL_MS", 30000) / 1000
    while True:
        await asyncio.sleep(interval_s)
        svc.sync_states()
        svc.sync_weather_forecast()


async def main_loop():
    asyncio.create_task(setup_wifi())
    asyncio.create_task(ha_sync_task())

    current_view = DefaultView()

    while True:
        if current_view_state["mode"] == "default":
            shutdown_event = shutdown_event_default
        else:
            shutdown_event = shutdown_event_focused

        await app_loop(current_view, shutdown_event)

        next_view_class = current_view_state.get("next_view_class")
        if next_view_class:
            view_kwargs = current_view_state.get("next_view_kwargs", {})
            current_view = next_view_class(**view_kwargs)
            current_view_state["next_view_class"] = None
            current_view_state["next_view_kwargs"] = {}
        else:
            break


def main():
    SplashView().render()
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
