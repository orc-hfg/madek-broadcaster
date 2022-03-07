from datetime import datetime
from pathlib import Path

from pyglet.event import EventDispatcher

from display.mediadisplay import MediaDisplay
from system.config import Config


class Dispatcher(EventDispatcher):
    """
    This is where the entire logic/magic is happening ...
    """

    def __init__(self, screens_):
        EventDispatcher.__init__(self)
        self._screens = []
        for s in screens_:
            self._screens.append(s)
        self._program = None
        self._config = Config()

    def set_program(self, program_):
        self._program = program_

    @property
    def program(self):
        return self._program

    @property
    def playlist(self):
        return self._program.playlist

    def update(self):
        # called by the playlist
        print('playlist update')
        self.start()

    def start(self):
        # combine screens and content
        screens = self.__find_empty_screens(True)
        content = []
        # find enough content for all empty screens
        while len(content) < len(screens)-1:
            e, i = self._program.get_next(True)
            # check whether program delivered an entry
            if not e:
                break
            t = ScreenEntry(e, None, i)
            content.append(t)
        # find a screen for each content item with fitting orientation
        for t in content:
            for s in screens:
                if t.entry and t.entry.orientation == s.orientation:
                    t.screen = s
                    screens.remove(s)
                    break
        # fill remaining screens with content
        for s in screens:
            for t in content:
                if not t.screen:
                    t.screen = s
                    screens.remove(s)
                    break
        # make remaining screen the info screen
        self._info_screen = screens[0]
        for s in self._screens:
            s.set_info_mode(s==self._info_screen)
        # play content
        for t in content:
            self.play_media_on_screen(t.screen, t.entry, t.index)
        if self._info_screen:
            self._info_screen.update_info_layout()

    def play_media(self, media_entry_, index_=None):
        """"
        Finds a screen for the next media entry - optionally with swapping places with the info screen.
        """
        # find an empty screen
        available_screen = None
        for s in self._screens:
            if s.is_empty:
                available_screen = s
                break
        if available_screen:
            # swap with info screen?
            if self._info_screen:
                    if abs(available_screen.orientation - media_entry_.orientation) \
                            > abs(self._info_screen.orientation - media_entry_.orientation):
                        self._info_screen.set_info_mode(False)
                        self._info_screen, available_screen = available_screen, self._info_screen
                        self._info_screen.set_info_mode(True)
            self.play_media_on_screen(available_screen, media_entry_, index_)
            if self._info_screen:
                self._info_screen.update_info_layout()
        else:
            print('No empty screen!')

    def play_media_on_screen(self, screen_, media_entry_, index_=None):
        """
        Triggers the actual display of content on a specific screen.
        At this point the content show be validated.
        :param screen_: Screen used for the content.
        :param media_entry_: MediaEntryData to be shown.
        :param collection_: Collection that contains the MediaEntry
        :return: None
        """
        print('play_media_on_screen {} - {} - {} sec.'.format(screen_, media_entry_, media_entry_.duration))
        media_display_ = MediaDisplay(media_entry_, screen_, self._program, index_)
        media_display_.push_handlers(on_end=self.on_screen_ready)
        screen_.set_media(media_display_)
        self.log_media(media_entry_)

    def on_screen_ready(self, media_display_, screen_):
        """
        Triggered whenever a MediaDisplay is finished.
        :param media_display_: MediaDisplay that contains the MediaEntryData
        :param screen_: Screen where it was shown.
        :return: None
        """
        # print('on_screen_ready %s' % screen_.index)
        screen_.clear_media()
        # Pull next entry.
        entry, index = self._program.get_next(True)
        if entry:
            self.play_media(entry, index)
        else:
            # TODO: do something useful ... or do I handle this elsewhere
            print('no entry')

    def __find_empty_screens(self, include_info_: object = False) -> object:
        e = []
        for s in self._screens:
            if not s.media:
                if s.is_info == False or s.is_info == include_info_:
                    e.append(s)
        return e

    @property
    def entries_len(self):
        if self._program:
            return self._program.length
        return 0

    def log_media(self, media_entry_):
        with open(str(Path(self._config.log_dir,'last_media_entry.txt')), 'w') as f:
            f.write('{} {}\n'.format(datetime.now().strftime('%H:%M:%S'),media_entry_.uuid))


class ScreenEntry():

    def __init__(self, entry_, screen_=None, index_=None):
        self.entry = entry_
        self.screen = screen_
        self.index = index_