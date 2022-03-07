class CollectionData():
    __instances = []

    @classmethod
    def get_instance(cls, id_):
        """

        :param id_: UUID from Madek
        :type id_: str
        """
        for c in cls.__instances:
            if c.id == id_:
                return c
        c = CollectionData(id_)
        cls.__instances.append(c)
        return c

    def __init__(self, id_):
        self.id = id_
        self.meta_data = {}
        self.media_entries = []
        self.collections = []

    def set_meta_datum(self, key_, value_):
        self.meta_data[key_] = value_

    def get_meta_datum(self, key_):
        return self.meta_data[key_]

    def get_meta_data(self):
        return self.meta_data
