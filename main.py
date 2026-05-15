import asyncio

from src.views import SplashView
from src.views import DefaultView
from src.core import setup_wifi

async def _app_loop():
    # switch to default view
    default_view = DefaultView()
    while True:
        # allow async tasks to run
        # see: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
        await asyncio.sleep(0)
        default_view.render()

def main():
    SplashView().render()
    asyncio.create_task(setup_wifi())

    # run application loop
    asyncio.run(_app_loop())

if __name__ == "__main__":
    main()
