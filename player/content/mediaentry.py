import os
import random
from tempfile import NamedTemporaryFile

import pyglet
import requests

from content.apidata import ApiData
from system.config import Config


class MediaEntryData(ApiData):

    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'document'

    # static shortcuts for the return values of self.orientation
    LANDSCAPE = -1
    SQUARE = 0
    PORTRAIT = 1

    @classmethod
    def get_instance(cls, id_: str, json_: dict=None):
        i = cls.find(id_)
        if i is None:
            i = MediaEntryData(id_)
            cls.instances[i.id] = i
        if json_:
            i.parse_data(json_)
        return i

    @classmethod
    def get_orientation(cls, width_: int, height_: int):
        if width_ > height_:
            return cls.LANDSCAPE
        elif height_ > width_:
            return cls.PORTRAIT
        return cls.SQUARE

    def __init__(self, id_: str):
        super(MediaEntryData, self).__init__(id_)
        self.created_at = None
        self.uuid = None
        self.is_published = None
        self.responsible_user_id = None
        self.file_data = None
        self.file = None
        self.image = None
        self.video = None
        if Config().dev_mode:
            self.duration = random.randint(3, 5)
        else:
            self.duration = random.randint(60, 120)

    def set_file_data(self, file_data_):
        self.file_data = file_data_

    def set_file(self, file_):
        self.file = file_
        self.file.push_handlers(on_cached=self.on_file_cached)

    def on_file_cached(self, file_):
        pass

    def parse_data(self, json_: dict):
        self.uuid = json_['id']
        self.created_at = json_['created_at']
        self.is_published = json_['is_published']
        self.responsible_user_id = json_['responsible_user_id']

    @property
    def media_type(self):
        if self.file_data and self.file_data.media_type:
            return self.file_data.media_type
        return None

    @property
    def is_image(self):
        return self.media_type == MediaEntryData.IMAGE

    @property
    def is_video(self):
        return self.media_type == MediaEntryData.VIDEO

    @property
    def is_audio(self):
        return self.media_type == MediaEntryData.AUDIO

    @property
    def is_document(self):
        return self.media_type == MediaEntryData.DOCUMENT

    @property
    def width_height(self):
        # Check first the actual size of the loaded file and then as a fallback the values from the API.
        if self.file and self.file.width and self.file.height:
            return self.file.width, self.file.height
        elif self.file_data and len(self.file_data.previews) > 0:
            return self.file_data.get_preview().width_height
        return None, None

    @property
    def orientation(self):
        """
        :return: MediaEntryData.LANDSCAPE, MediaEntryData.SQUARE, MediaEntryData.PORTRAIT
        """
        w, h = self.width_height
        return MediaEntryData.get_orientation(w, h)

    @property
    def file_url(self):
        # TODO: Decide which data stream should be shown.
        if self.file_data and len(self.file_data.previews) > 0:
            return self.file_data.get_preview().data_stream
        return None

    def __str__(self):
        s = 'MediaEntryData {}'.format(self.uuid)
        return s


class MediaFile(pyglet.event.EventDispatcher):

    __SUFFIXES = {MediaEntryData.IMAGE: '.jpg', MediaEntryData.VIDEO: '.mp4',
                  MediaEntryData.AUDIO: '.mp3', MediaEntryData.DOCUMENT: '.jpg'}

    def __init__(self, entry_: MediaEntryData):
        super(MediaFile, self).__init__()
        self.__entry = entry_
        self.__temp_file = None
        self.__image_source = None
        self.__video_source = None
        self.__entry.set_file(self)

    def cache(self):
        if self.__temp_file:
            self.__temp_file.close()
        self.__temp_file = NamedTemporaryFile(suffix=self.__suffix, delete=False)
        response = None
        attempts = 0
        while not response or response.status_code != 200 and attempts < 3:
            response = requests.get('{}{}'.format(
                Config().server, self.__entry.file_url), auth=Config().api_auth)
            if response.status_code == 200:
                self.__temp_file.write(response.content)
                if self.__entry.is_image:
                    self.__image_source = pyglet.image.load(self.__temp_file.name)
                elif self.__entry.is_video:
                    self.__video_source = pyglet.media.load(self.__temp_file.name)
                self.dispatch_event('on_cached', self)
                return None
            else:
                print('Problem caching {}'.format(self.__entry.file_url))
                attempts += 1
        print('Failed to cache file! {}'.format(self.__entry))

    def delete(self):
        if self.__temp_file:
            self.__temp_file.close()
            self.__temp_file = None
        self.__image_source = None
        self.__video_source = None

    @property
    def width(self):
        if self.__image_source:
            return self.__image_source.width
        elif self.__video_source and self.__video_source.video_format:
            return self.__video_source.video_format.width
        return None

    @property
    def height(self):
        if self.__image_source:
            return self.__image_source.height
        elif self.__video_source and self.__video_source.video_format:
            return self.__video_source.video_format.height
        return None

    @property
    def texture(self):
        if self.__entry.is_image:
            if not self.__image_source:
                return None
            return self.__image_source.get_texture()
        return None

    @property
    def source(self):
        if self.__image_source:
            return self.__image_source
        elif self.__video_source:
            return self.__video_source
        return None

    @property
    def __suffix(self):
        if self.__entry.media_type in MediaFile.__SUFFIXES:
            return MediaFile.__SUFFIXES[self.__entry.media_type]
        return None


MediaFile.register_event_type('on_cached')


class MediaFileData():
    def __init__(self, server_: str, json_: dict):
        self.id = json_['id']
        self.filename = json_['filename']
        self.media_entry_id = json_['media_entry_id']
        self.size = json_['size']
        # TODO: Fill once the API delivers it.
        self.media_type = self.guess_media_type()
        # TODO: Fill once the API delivers it.
        self.content_type = None
        self.data_stream = '{}{}'.format(server_, json_[
            '_json-roa']['relations']['data-stream']['href'])
        self.previews = []

    def add_preview(self, preview_):
        # TODO: Remove once the API delivers this for MediaFile.
        if self.media_type is None or self.media_type is MediaEntryData.IMAGE:
            self.media_type = preview_.media_type
        self.previews.append(preview_)

    def get_preview(self, size_: str="x_large"):
        # maximum, x_large, large, medium, small_125, small
        # look for videos first
        for i in self.previews:
            if i.content_type == 'video/mp4':
                return i
        for i in self.previews:
            if i.thumbnail == size_:
                return i
        return None

    def guess_media_type(self):
        # This is just an ugly way to determine the media type as the API doesn't tell.
        image_extensions = ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.bmp', '.gif', '.psd']
        video_extensions = ['.mov', '.mkv', '.mp4', '.avi', '.mpg', '.mpeg', '.3pg', '.vob']
        sound_extensions = ['.aif', '.aiff', '.wav', '.mp3', '.m4a', '.aac']
        document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.ai', '.epub']
        filename, file_extension = os.path.splitext(self.filename)
        if file_extension.lower() in image_extensions:
            return MediaEntryData.IMAGE
        elif file_extension.lower() in video_extensions:
            return MediaEntryData.VIDEO
        elif file_extension.lower() in sound_extensions:
            return MediaEntryData.AUDIO
        elif file_extension.lower() in document_extensions:
            return MediaEntryData.DOCUMENT
        print('#### unrecognized file extension: {} ####'.format(file_extension))
        return None

    def __str__(self):
        s = 'MediaFileData: %s - %s' % (self.filename, self.data_stream)
        return s


class PreviewData():
    def __init__(self, server_, json_):
        self.id = json_['id']
        self.media_type = json_['media_type']
        self.content_type = json_['content_type']
        self.filename = json_['filename']
        self.thumbnail = json_['thumbnail']
        # Only to be used carefully because the API doesn't provide real sizes.
        self.width = json_['width']
        self.height = json_['height']
        self.created_at = json_['created_at']
        self.updated_at = json_['updated_at']
        self.media_file_id = json_['media_file_id']
        self.data_stream = '{}'.format(json_[
            '_json-roa']['relations']['data-stream']['href'])

    @property
    def width_height(self):
        return self.width, self.height

    def set_size(self, width_, height_):
        # used to overwrite values from JSON with actual ones from cached file
        self.width = width_
        self.height = height_
