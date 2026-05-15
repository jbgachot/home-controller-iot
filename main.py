import asyncio
import config

from src.views import SplashView
from src.core import setup_wifi

def main():
    SplashView().render()

    asyncio.create_task(setup_wifi())


if __name__ == "__main__":
    main()
