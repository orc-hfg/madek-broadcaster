from content.apidata import ApiData
from operator import attrgetter


class CollectionData(ApiData):
    @classmethod
    def get_instance(cls, id_, json_=None):
        i = cls.find(id_)
        if i is None:
            i = CollectionData(id_)
            cls.instances[i.id] = i
        if json_:
            i.parse_data(json_)
        return i

    def __init__(self, id_):
        """
        :param id_: UUID from Madek
        :type id_: str
        """
        super(CollectionData, self).__init__(id_)
        self.media_entries = []
        self.collections = []
        self.created_at = None
        self.creator_id = None
        self.responsible_user_id = None

    def set_media_entries(self, media_entries_list):
        self.media_entries = media_entries_list

    def add_media_entry(self, media_entry):
        self.media_entries.append(media_entry)

    def sort_on(self, *args):
        """
        Sorts media entries.
        :param *args: meta-key names as strings, replace ':' with '__', i.e. 'madek_core__title'
        :return: None
        """
        args = list(args)
        self.media_entries = sorted(self.media_entries, key=attrgetter(*args))

    @property
    def media_entries_len(self):
        return len(self.media_entries)

    def parse_data(self, json_):
        self.created_at = json_['created_at']
        self.creator_id = json_['creator_id']
        self.responsible_user_id = json_['responsible_user_id']
        # clear previous items
        self.media_entries = []
        self.collections = []

    def __str__(self):
        s = 'CollectionData {}'.format(self.id)
        return s
