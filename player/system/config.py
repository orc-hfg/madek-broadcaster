from pathlib import Path


def get_green():
    return 122, 157, 41, 255


class Config:
    """
    Contains all configurations for the player.
    """

    META_DATA_MINIMUM = ['madek_core:authors', 'madek_core:title', 'madek_core:copyright_notice']
    GREEN = (122, 157, 41, 255)
    FONT = 'Open Sans Medium'
    instance = None

    class __Config:

        def __init__(self):
            self.__api_auth = None
            self.__server = None
            self.__meta_datum_white_list = []
            self.__dev_mode = False

        def set_server(self, server_):
            self.__server = server_

        def set_api_auth(self, api_auth):
            """
            :param api_auth: tuple with user and password
            :type api_auth: type tuple
            """
            # api_auth is a tuple with user and password
            self.__api_auth = api_auth

        def set_meta_data_white_list(self, list_=None):
            """
            Set an optional white list of meta key.
            :param list_: None or e.g. ['madek_core:title', 'madek_core:keywords']
            :type list_: list
            :return:
            """
            self.__meta_datum_white_list = list_

        def set_dev_mode(self, dev_mode_):
            self.__dev_mode = dev_mode_

        @property
        def server(self):
            return self.__server

        @property
        def api_auth(self):
            return self.__api_auth

        @property
        def meta_data_white_list(self):
            return list(set(self.__meta_datum_white_list) | set(Config.META_DATA_MINIMUM))

        @property
        def dev_mode(self):
            return self.__dev_mode

        @property
        def log_dir(self):
            return str(Path(Path.home(), 'player_log'))


    def __init__(self):
        if not Config.instance:
            Config.instance = Config.__Config()

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)
