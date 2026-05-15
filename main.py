import asyncio

from src.views import SplashView
from src.views import DefaultView
from src.core import setup_wifi
from src.core import app_loop


def main():
    SplashView().render()
    asyncio.create_task(setup_wifi())
    asyncio.run(app_loop(DefaultView()))

if __name__ == "__main__":
    main()
