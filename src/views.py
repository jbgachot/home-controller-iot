from core import display
from core import rgb
from core import presto

# sizes & spacing
WIDTH, HEIGHT = display.get_bounds()

# colors
WHITE = rgb(255, 255, 255)
BLACK = rgb(0, 0, 0)


class SplashView:
    def render(self):
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.text("  Loading\nCompresto", 20, HEIGHT // 2 - 24, WIDTH, 4)
        presto.update()
