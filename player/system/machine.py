import math
import os

import pyglet

from system.screen import Screen


class Machine:
    """
    Singleton class
    """

    instance = None

    class __Machine:

        windows = []
        screens = []
        singleScreen = False
        scale = 1

        def __init__(self, font_directory):
            """

            :type font_directory: str
            """
            self.platform = None
            self.display = None
            self.font_directory = font_directory
            pyglet.gl.glEnable(pyglet.gl.GL_TEXTURE_2D)  # Do I need this here?
            self.check()

        def check(self):
            """
            Checks the system attributes.
            """

            self.platform = pyglet.window.get_platform()
            self.display = self.platform.get_default_display()

            if len(self.display.get_screens()) == 1:
                self.singleScreen = True
                s = self.display.get_default_screen()
                self.scale = (s.width-40) / (2*Screen.RESOLUTION_WIDTH + Screen.RESOLUTION_HEIGHT)

            for screen in self.display.get_screens():
                print(screen)

            self.load_fonts()

        def load_fonts(self):
            for f in ['Regular', 'Italic', 'Bold', 'BoldItalic', 'Semibold', 'SemiboldItalic']:
                fn = 'OpenSans-{}.ttf'.format(f)
                pyglet.font.add_file(os.path.join(self.font_directory, fn))
            pyglet.font.load('Open Sans')
            pyglet.font.load('Open Sans Semibold')

        def create_screen(self):
            """
            Return single Screen instances.
            """
            s = None
            i = len(self.screens)
            if i < 3:
                if i != 1:
                    w = Screen.RESOLUTION_WIDTH
                    h = Screen.RESOLUTION_HEIGHT
                else:
                    h = Screen.RESOLUTION_WIDTH
                    w = Screen.RESOLUTION_HEIGHT
                screen = 0 if self.singleScreen else i
                s = Screen(i, self.display.get_screens()[screen], self.singleScreen, w, h, self.scale)
                # temp
                if i == 1:
                    s.set_info_mode(True)

                # position the window
                if self.singleScreen:
                    screen_width = self.display.get_screens()[0].width
                    s.set_location(int(max(10, min(screen_width - self.scale * w - 10,
                                                   (len(self.screens) + 0.5) * math.floor(
                                                       screen_width / 3) - self.scale * 0.5 * w))),
                                   max(80, 40 + int(0.5 * self.scale * (w - h))))
                self.screens.append(s)
            return s

    def __init__(self, font_directory):
        if not Machine.instance:
            Machine.instance = Machine.__Machine(font_directory)

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)
