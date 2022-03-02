from enum import Enum
from functools import lru_cache
from optparse import OptionParser
from random import uniform
from time import sleep

import vgamepad as vg


class SetupOptions(Enum):
    LOAD = 'load'
    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'
    RANDOM = 'random'


class Controller:
    def __init__(self):
        self.gamepad = vg.VDS4Gamepad()
        self.x, self.y = 0.0, 0.0

    def load_state(self):
        self.gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
        self.gamepad.update()
        sleep(0.01)
        self.gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
        self.gamepad.update()
        sleep(0.01)

    def random_movement(self):
        self.gamepad.left_joystick_float(x_value_float=uniform(-1.0, 1.0),
                                         y_value_float=uniform(-1.0, 1.0))
        self.gamepad.update()
        sleep(0.167)

    def do_movement(self, x, y):
        x, y = clamp(x), clamp(y)
        if x != self.x or y != self.y:
            self.x, self.y = x, y
            self.gamepad.left_joystick_float(x_value_float=x, y_value_float=y)
            self.gamepad.update()

    def setup_UP(self):
        self.do_movement(0, 1)
        sleep(0.1)
        self.do_movement(0, 0)
        sleep(0.1)

    def setup_DOWN(self):
        self.do_movement(0, -1)
        sleep(0.1)
        self.do_movement(0, 0)
        sleep(0.1)

    def setup_LEFT(self):
        self.do_movement(-1, 0)
        sleep(0.1)
        self.do_movement(0, 0)
        sleep(0.1)

    def setup_RIGHT(self):
        self.do_movement(1, 0)
        sleep(0.1)
        self.do_movement(0, 0)
        sleep(0.1)


@lru_cache(maxsize=2 ** 20)
def clamp(n, minimum=-1.0, maximum=1.0):
    # TODO Return to this
    if n > maximum:
        n = float('0.' + str(n).replace('.', ''))
    if n < minimum:
        n = float('-0.' + str(n).replace('.', '').replace('-', ''))
    return max(minimum, min(n, maximum))


if __name__ == "__main__":
    parser = OptionParser()

    parser.add_option('-s', '--setup', dest='setup', choices=[o.value for o in SetupOptions],
                      help='Setup options: [load, up, down, left, right, random]')

    options, _ = parser.parse_args()

    setup = options.setup

    controller = Controller()
    sleep(0.1)
    while True:
        if setup == SetupOptions.LOAD.value:
            controller.load_state()
        elif setup == SetupOptions.UP.value:
            controller.setup_UP()
        elif setup == SetupOptions.DOWN.value:
            controller.setup_DOWN()
        elif setup == SetupOptions.LEFT.value:
            controller.setup_LEFT()
        elif setup == SetupOptions.RIGHT.value:
            controller.setup_RIGHT()
        elif setup == SetupOptions.RANDOM.value:
            controller.random_movement()
        else:
            print('Invalid option')
            break
