from functools import lru_cache
from random import uniform
from time import sleep

import vgamepad as vg


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
    controller = Controller()
    sleep(0.1)
    while True:
        controller.load_state()  # Replace this line with setup functions
