import math

import pyglet
from pyglet.gl import *
from pyglet.text import Label
from pyglet.text.layout import TextLayout
from pyglet.window import Window

from content.mediaentry import MediaEntryData
from display.mediadisplay import MediaDisplay
from system.config import Config


class Screen(Window):

    RESOLUTION_WIDTH = 1920
    RESOLUTION_HEIGHT = 1080
    PADDING = 80

    # contains the MediaDisplay instances played on the content screens
    # so that the info screen has access to them
    _content = []
    _captions = []

    def __init__(self, index_, screen_, single_screen_=True, width_=RESOLUTION_WIDTH, height_=RESOLUTION_HEIGHT,
                 scale_=1):

        self.__index = index_
        self.__virtual_width = width_
        self.__virtual_height = height_
        self.__info_mode = False
        # MediaDisplay
        self.__caption = None
        self._insert = None
        self._program = None
        # For each new Screen add empty entries in the following class lists
        Screen._content.append(None)
        Screen._captions.append(None)
        self.orientation = MediaEntryData.get_orientation(self.__virtual_width, self.__virtual_height)
        # only for info screens
        self._content_width = self.get_width - 2 * Screen.PADDING
        full_screen = not single_screen_
        super(Screen, self).__init__(width=math.floor(scale_ * width_), height=math.floor(scale_ * height_),
                                     caption='Window {}'.format(
                                         index_ + 1), screen=screen_, fullscreen=full_screen, style=Window.WINDOW_STYLE_TOOL)
        if full_screen:
            self.set_mouse_visible(False)
        glEnable(GL_TEXTURE_2D)
        glScalef(scale_, scale_, scale_)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    @property
    def media(self):
        return Screen._content[self.__index]

    @property
    def get_width(self):
        return self.__virtual_width

    @property
    def get_height(self):
        return self.__virtual_height

    @property
    def is_info(self):
        return self.__info_mode

    @property
    def index(self):
        return self.__index

    def set_info_mode(self, info_=True):
        """
        Switches between both modes.
        :param info_:
        :return:
        """
        if info_ != self.__info_mode:
            if info_:
                # switch from media to info mode
                self._insert = self.create_insert()
                Screen._content[self.__index] = None
                Screen._captions[self.__index] = None
                self.__caption = None
                pass
            else:
                # switch from info to media mode
                self._insert = None
                self._program = None
            self.__info_mode = info_

    def set_media(self, media_):
        # expects MediaDisplay
        if not self.__info_mode and type(media_) is MediaDisplay:
            if self.media:
                self.media.hide()
            Screen._content[self.__index] = media_
            self.media.show()
            caption_lines = []
            # if media_.index:
            #     caption_lines.append(str(media_.index))
            for i in Config.META_DATA_MINIMUM:
                v = media_.media_entry.get_meta_datum(i)
                if v:
                    caption_lines.append(v)
            caption = '\n'.join(caption_lines)
            self.__caption = MediaCaption(self.media.area, self.media, caption)

    def create_insert(self):
        insert_text = 'Sender Medienarchiv'
        insert_text_size = self.find_text_size(insert_text, self._content_width)
        insert = Label(insert_text, font_name=Config.FONT, bold=False, font_size=insert_text_size,
                       color=Config.GREEN, anchor_x='left', anchor_y='top')
        insert.x = Screen.PADDING
        insert.y = self.get_height - Screen.PADDING
        return insert

    def set_program_info(self, program_):
        t = program_.name
        s = Screen.find_text_size(t, self._content_width)
        d = Screen.get_formatted_text(t, s)
        self._program = Label(t, font_name=Config.FONT, bold=False, font_size=s,
                              color=Config.GREEN, anchor_x='left', anchor_y='top')
        self._program.x = Screen.PADDING
        self._program.y = self._insert._y - self._insert.content_height - Screen.PADDING

    def update_info_layout(self):
        # detect available space
        top = self._insert._y - self._insert.content_height - Screen.PADDING
        # find content and count different programs
        content = [] # MediaDisplay
        programs = [] # contexts of the content
        for m in Screen._content:
            if m:
                content.append(m)
                # Is this a new program?
                new_program = True
                for c in programs:
                    if m.program and c == m.program:
                        new_program = False
                        break
                if new_program:
                    programs.append(m.program)
        # only show context info if all contents have the same
        if len(programs) == 1 and programs[0]:
            self.set_program_info(programs[0])
            top = self._program._y - self._program.content_height - Screen.PADDING
        else:
            self._program = None
        # define space for content info
        landscape = self.orientation == MediaEntryData.LANDSCAPE
        x = Screen.PADDING
        if landscape:
            w = (self._content_width - (len(content)-1) * Screen.PADDING) / len(content)
            h = top - Screen.PADDING
        else:
            w = self._content_width
            h = (top - Screen.PADDING - (len(content)-1) * Screen.PADDING) / len(content)
        for m in content:
            if m:
                # get text to display
                pointer = ''
                if m.screen.index < self.index:
                    pointer = (self.index-m.screen.index)*'<'
                elif m.screen.index > self.index:
                    pointer = (m.screen.index-self.index)*'>'
                t = '{} {}'.format(pointer, m.media_entry.serialize_meta_data(m.program.meta_data_white_list, ' | ', ' ¶ '))
                s = Screen.find_text_size(t, w, h)
                d = Screen.get_formatted_text(t, s)
                c = InfoBox(d, x, top, w)
                Screen._captions[m.screen.index] = c
                if landscape:
                    x = x + w + Screen.PADDING
                else:
                    top = top - h - Screen.PADDING

    def clear_media(self):
        if Screen._content[self.__index]:
            Screen._content[self.__index].hide()
        Screen._content[self.__index] = None

    @property
    def is_info(self):
        return self.__info_mode == True

    @property
    def is_empty(self):
        return not self.media and not self.__info_mode

    @staticmethod
    def find_text_size(text_:str, max_width_:float, max_height_:float=None, bold_:bool=False):
        """
        :return: float
        """
        s = 50
        if max_height_:
            # take max_width_ as fixed and find text size for max_height_
            while Screen.get_text_height(text_, s, max_width_) < max_height_:
                s += 1
            while Screen.get_text_height(text_, s, max_width_) > max_height_:
                s -= 1
            # also check width
            _, w = Screen.get_text_height_width(text_, s, max_width_)
            if w > max_width_:
                while w > max_width_:
                    s -= 1
                    _, w = Screen.get_text_height_width(text_, s, max_width_)
        else:
            # find text size
            while Screen.get_text_width(text_, s, bold_) < max_width_:
                s += 1
            while Screen.get_text_width(text_, s, bold_) > max_width_:
                s -= 1
        return s

    @staticmethod
    def get_text_width(text_:str, size_:float, bold_:bool=False):
        """
        :return: float
        """
        l = Label(text_, font_name=Config.FONT, bold=bold_,
                  font_size=size_, anchor_x='left',
                  anchor_y='top')
        r = l.content_width
        l.delete()
        return r

    @staticmethod
    def get_text_height(text_:str, size_:float, width_:float):
        """
        :return: float
        """
        d = Screen.get_formatted_text(text_, size_)
        t = InfoBox(d, 0, 0, width_)
        r = t.content_height
        t.delete()
        return r

    @staticmethod
    def get_text_height_width(text_:str, size_:float, width_:float):
        """
        :return: float
        """
        d = Screen.get_formatted_text(text_, size_)
        t = InfoBox(d, 0, 0, width_)
        h = t.content_height
        w = t.content_width
        t.delete()
        return h, w

    @staticmethod
    def get_formatted_text(text_, size_, align_='left'):
        d = pyglet.text.decode_text(text_)
        d.set_style(start=0, end=0,
                    attributes={'font_name': Config.FONT, 'font_size': size_, 'color': Config.GREEN, 'align': align_})
        return d

    def on_draw(self):
        self.clear()
        if self.__info_mode:
            self._insert.draw()
            if self._program:
                self._program.draw()
            for c in Screen._captions:
                if type(c) is InfoBox:
                    c.draw()
        else:
            if self.media:
                self.media.draw()
            if self.__caption:
                self.__caption.draw()

    def __str__(self):
        return 'Screen {}'.format(self.index+1)

    def on_key_press(self, symbol_, modifiers_):
        super(Screen, self)
        pyglet.app.exit()


class MediaCaption(TextLayout):

    PADDING = 40

    def __init__(self, area_, width_, text_):
        d = Screen.get_formatted_text(text_, 36)
        w = area_.width - 2 * MediaCaption.PADDING
        h = area_.height - 2 * MediaCaption.PADDING
        TextLayout.__init__(self, d, width=w, height=h, multiline=True, wrap_lines=True)
        self.anchor_x = 'left'
        self.anchor_y = 'top'
        self.x = area_.x + MediaCaption.PADDING
        self.y = area_.y + self.content_height + MediaCaption.PADDING - 6


class InfoBox(TextLayout):
    def __init__(self, document_, x_, y_, w_, h_=None, align_='left', multi_=True):
        TextLayout.__init__(self, document_, width=w_, height=h_, multiline=multi_, wrap_lines=multi_)
        self.anchor_x = 'left'
        self.anchor_y = 'top'
        self.x = x_
        self.y = y_

    def __str__(self):
        s = 'InfoBox {} / {} / {} / {}'.format(self.x,self.y,self.content_width,self.content_height)
        return s

