from random import shuffle

from pyglet.event import EventDispatcher

from content.api import MediaEntryParams
from system.config import Config
from content.apidata import KeywordData, PeopleData


class Program(EventDispatcher):

    def __init__(self, api_, json_=None):
        EventDispatcher.__init__(self)
        self._api = api_
        self._meta_data_white_list = Config().meta_data_white_list
        self._limit = 20
        if json_:
            self.parse_json(json_)
        self._limit_selection = self._limit
        self._start_url = None
        self._playlist = None
        self.__index = None

    def parse_json(self, json_):
        self._name = json_['name']
        self._params = MediaEntryParams(json_.get('parameters'))
        self._meta_data_white_list = json_.get('meta_data')
        self._limit = int(json_.get('limit', self._limit))
        if json_.get('limit_selection'):
            self._limit_selection = int(json_.get('limit_selection'))

    def set_limit(self, limit_=0):
        self._limit = limit_

    async def load(self, preload_media_=False):
        print(self.start_url)
        limit = max(self._limit, self._limit_selection)
        self.__index = None
        self._playlist = []
        playlist = []
        for m in await self._api.get_media_entries(self.start_url, limit, self._meta_data_white_list, preload_media_):
            # only use images and videos
            if m.is_image or m.is_video:
                playlist.append(m)
        if self._limit_selection > self._limit:
            shuffle(playlist)
        if self._limit > 0:
            self._playlist = playlist[:self._limit]
        else:
            self._playlist = playlist[:]

    def sort(self):
        pass

    def get_next(self, count_=False):
        """
        Returns the next entry and its index.
        :param count_: Boolean for advancing the index.
        :return: MediaEntryData, int
        """
        n = None
        if self._playlist.__len__() > 0:
            if self.__index is None:
                self.__index = 0
            if self.__index < self._playlist.__len__():
                n = self._playlist[self.__index]
                if count_:
                    self.__index += 1
        return n, self.__index

    @property
    def name(self):
        return self._name

    @property
    def playlist(self):
        return self._playlist

    @property
    def length(self):
        if self.__index is None:
            self.__index = 0
        if self._playlist:
            return self._playlist.__len__() - self.__index
        return 0

    @property
    def valid(self):
        return self.length > 0

    @property
    def meta_data_white_list(self):
        return self._meta_data_white_list

    @property
    def start_url(self):
        if self._params:
            return self._params.url
        return None

    @property
    def web_url(self):
        """
        Returns a url for the Madek web app and not the API.
        :return: String
        """
        if self._params:
            return self._params.web_url
        return None


class FollowupProgram(Program):

    def __init__(self, api_):
        super(FollowupProgram, self).__init__(api_)

    def set_reference(self, reference_program_):
        print('set_reference {}'.format(reference_program_))
        # define start path based of reference program
        last_entry = reference_program_.playlist[-1]
        print('last_entry {}'.format(last_entry))
        hooks = []
        keywords = last_entry.get_meta_datum('madek_core:keywords', False)
        if type(keywords)is list:
            hooks += keywords
        authors = last_entry.get_meta_datum('madek_core:authors', False)
        if type(authors) is list:
            hooks += authors
        project_type = last_entry.get_meta_datum('zhdk_bereich:project_type', False)
        if type(project_type) is list:
            hooks += project_type
        material = last_entry.get_meta_datum('media_content:portrayed_object_materials', False)
        if type(material) is list:
            hooks += material
        types = last_entry.get_meta_datum('media_content:type', False)
        if type(types) is list:
            hooks += types
        shuffle(hooks)
        print('hooks {}'.format(hooks))
        # handle case that there are no keywords
        hook = hooks[0] if len(hooks)>0 else None
        if hook:
            print('hook {} {}'.format(type(hook), hook.id))
            if type(hook) is KeywordData:
                print('meta_key_id {}'.format(hook.meta_key_id))
                if hook.meta_key_id == 'madek_core:keywords':
                    self._name = 'Schlagwort {}'.format(hook)
                elif hook.meta_key_id == 'zhdk_bereich:project_type':
                    self._name = 'Typ {}'.format(hook)
                elif hook.meta_key_id == 'zhdk_bereich:academic_year':
                    self._name = 'Studienabschnitt {}'.format(hook)
                elif hook.meta_key_id == 'media_content:type':
                    self._name = 'Disziplin {}'.format(hook)
                elif hook.meta_key_id == 'media_content:portrayed_object_materials':
                    self._name = 'Material/Format/Sprache {}'.format(hook)
                else:
                    self._name = str(hook)
                    print('---- unrecognized meta_key_id {} ----'.format(hook.meta_key_id))
                self._params = MediaEntryParams({"filter_by": {"meta_data": [{"key": hook.meta_key_id, "value": hook.id}]}})
            elif type(hook) is PeopleData:
                # TODO: Maybe make do author selection?
                self._name = 'Person {}'.format(hook)
                self._params = MediaEntryParams({"filter_by": {"meta_data": [{"key": "any", "value": hook.id, "type": "MetaDatum::People"}]}})
            return True
        else:
            return False
