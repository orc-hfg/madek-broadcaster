import tempfile

import pyglet

from content.mediaentry import MediaFile


class MediaDisplay(pyglet.event.EventDispatcher):
    """
    This is where a MediaEntry that is basically a data object turns into something 
    that is loaded and can be shown on a specific screen.
    """

    def __init__(self, media_entry_, screen_, program_=None, index_=None):
        super(MediaDisplay, self).__init__()
        self.media_entry = media_entry_
        self.program = program_
        self.index = index_
        self.screen = screen_
        self.texture = None
        self.player = None
        if self.media_entry.is_video:
            self.player = pyglet.media.Player()  # for videos
            @self.player.event
            def on_eos():
                self.on_video_end(self)
        self.area = None

    def define_area(self):
        # Looks for a suitable position on the screen
        w, h = self.media_entry.width_height
        if w and h:
            # First init the are with the original size ...
            self.area = Area(0, 0, w, h)
            # .. and then scale and position it on the screen
            self.area.scale_to(
                self.screen.get_width, self.screen.get_height, 10, True, True)

    def show(self):
        # Called when the content appears on the screen.
        if not self.media_entry.file:
            self.media_entry.file = MediaFile(self.media_entry)
        if not self.media_entry.file.source:
            self.media_entry.file.cache()
        if self.media_entry.is_image:
            self.texture = self.media_entry.file.texture
        elif self.media_entry.is_video:
            self.player.queue(self.media_entry.file.source)
            self.player.play()
        pyglet.clock.schedule_once(self.on_timer_end, self.media_entry.duration)
        self.define_area()
        self.dispatch_event('on_show', self)

    def draw(self):
        a = self.area
        if self.media_entry.is_video and self.player:
            self.player.get_texture().blit(a.x, a.y, 0, a.width, a.height)
        elif self.texture:
            self.texture.blit(a.x, a.y, 0, a.width, a.height)

    def on_video_end(self):
        self.on_content_end()

    def on_timer_end(self, seconds_):
        # timer used for still images and to end videos
        self.on_content_end()

    def on_content_end(self):
        self.dispatch_event('on_end', self, self.screen)

    def hide(self):
        if self.player:
            self.player.delete()
        self.media_entry.file.delete()

MediaDisplay.register_event_type('on_show')
MediaDisplay.register_event_type('on_end')


class Area:
    def __init__(self, x_, y_, w_, h_):

        self.x = x_
        self.y = y_
        self.width = w_
        self.height = h_

    def scale_to(self, width_, height_, padding_=0, centered_=True, proportional_=True):

        scale_x = (width_ - 2 * padding_) / self.width
        scale_y = (height_ - 2 * padding_) / self.height

        if proportional_:
            scale_x = min(scale_x, scale_y)
            scale_y = scale_x

        self.width *= scale_x
        self.height *= scale_y

        if centered_:
            self.x = padding_ + 0.5 * (width_ - 2 * padding_ - self.width)
            self.y = padding_ + 0.5 * (height_ - 2 * padding_ - self.height)
        else:
            self.x = padding_
            self.y = padding_
