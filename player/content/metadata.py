class MetaData():
    def __init__(self, url_=None, title_=None, width_=None, height_=None, duration_=5):
        self._id = None
        self._url = url_
        self._title = title_
        self._width = width_
        self._height = height_
        self._duration = duration_

    def get_id(self):
        return self._id

    def get_url(self):
        return self._url

    def get_title(self):
        return self._title

    def get_width(self):
        return self._width

    def get_height(self):
        return self._width

    def get_width_height(self):
        return self._width, self._height

    def set_duration(self, duration_):
        # used to overwrite the duration that comes from the metadata with the
        # actual duration of a video file
        print('new duration: %d' % duration_)
        self._duration = duration_

    def get_duration(self):
        return self._duration

    def set_value(self, key_, value_):
        print('set_value ' + key_ + ' = ' + value_)
        pass
