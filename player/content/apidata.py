import textwrap

from system.config import Config


class ApiData():
    instances = {}

    @classmethod
    def find(cls, id_:str):
        """
        Class method that returns either an existing instance with the given id
        or a new one.
        :param id_: UUID from Madek
        :return: Returns either an existing instance with the given id or None.
        :rtype: ApiData
        """
        return cls.instances.get(id_)

    def __init__(self, id_:str):
        self.id = id_
        self.__meta_data = {}

    def set_meta_datum(self, meta_datum_):
        """
        Stores meta datum
        :param meta_datum_: meta datum
        """
        self.__meta_data[meta_datum_.meta_key_id] = meta_datum_

    def get_meta_datum(self, key_:str, enforce_string_:bool=True):
        """
        Returns the value of a given meta key.
        :param key_: string of a meta key
        :param enforce_string_: converts lists into strings
        :return: Either MetaDatum instance or serialized values
        """
        if key_ in self.__meta_data:
            return self.__meta_data[key_].get_value(enforce_string_)
        return None

    def serialize_meta_data(self, keys_:list=None, separator_:str=' | ', paragraph_separator_:str=None):
        values = []
        if not keys_:
            keys_ = Config().meta_data_white_list
        for key in keys_:
            value = self.get_meta_datum(key)
            if value:
                if type(value) == str:
                    # remove double linebreaks
                    value = value.replace('\r', '\n')
                    while value.find('\n\n') > -1:
                        value = value.replace('\n\n', '\n')
                    if paragraph_separator_:
                        value = value.replace('\n', paragraph_separator_)
                    # shorten text
                    value = textwrap.shorten(value, 500, placeholder='...')
                values.append(value)
        return separator_.join(values)

    def __getattr__(self, name_:str):
        """
        Allows generic access to meta keys. ':' is to be replaced with '__'.
        ApiData.madek_core__title thus will look for madek_core:title
        :param name_:
        :return: always a string, '' for empty meta keys for sorting
        """
        # This is needed to allow pickle support.
        if name_.startswith('__') and name_.endswith('__'):
            return super(ApiData, self).__getattr__(name_)
        name_ = name_.replace('__',':')
        # For missing values do not return None but an empty string to allow sorting.
        if self.get_meta_datum(name_):
            return self.get_meta_datum(name_)
        return ''


class MetaDatum():
    instances = {}

    @classmethod
    def find(cls, id_:str):
        """
        Class method that returns either an existing instance with the given id
        or a new one.
        :param id_: UUID from Madek
        :return: Returns either an existing instance with the given id or None.
        :rtype: MetaDatum
        """
        return cls.instances.get(id_)

    @classmethod
    def get_instance(cls, json_:dict):
        """
        Use always this class method to create new instances.
        :param json_: JSON from API
        :return: Returns either an existing instance with the given id or a new one.
        :rtype: MetaDatum
        """
        i = cls.find(json_['id'])
        if i is None:
            i = MetaDatum(json_)
            cls.instances[i.id] = i
        return i

    def __init__(self, json_:dict):
        self.id = json_['id']
        self.meta_key_id = json_.get('meta_key_id')
        self.type = json_.get('type')
        self.value = None # can either be a string or a list with MetaDatum instances
        if 'value' in json_ and type(json_['value']) is str:
            self.value = json_['value']

    def add_value(self, value_):
        if not self.value:
            self.value = []
        if type(self.value) is list:
            self.value.append(value_)

    def get_value(self, serialized_:bool=True, delimiter_:str=', '):
        if serialized_ and type(self.value) is list:
            values = []
            for v in self.value:
                if v:
                    values.append(v.get_value())
            return delimiter_.join(values)
        return self.value


class KeywordData(MetaDatum):

    @classmethod
    def get_instance(cls, json_:dict):
        i = cls.find(json_['id'])
        if i is None:
            i = KeywordData(json_)
            cls.instances[i.id] = i
        return i

    def __init__(self, json_):
        super(KeywordData, self).__init__(json_)
        self.__value = json_['term']

    def get_value(self, serialized_=True, delimiter_=', '):
        return self.__value

    def __str__(self):
        return self.__value


class PeopleData(MetaDatum):

    @classmethod
    def get_instance(cls, json_:dict):
        i = cls.find(json_['id'])
        if i is None:
            i = PeopleData(json_)
            cls.instances[i.id] = i
        return i

    def __init__(self, json_:dict):
        super(PeopleData, self).__init__(json_)
        self.first_name = json_.get('first_name')
        self.last_name = json_.get('last_name')
        self.pseudonym = json_.get('pseudonym')
        self.date_of_birth = json_.get('date_of_birth')
        self.date_of_death = json_.get('date_of_death')

    def get_value(self, serialized_:bool=True, delimiter_:str=', '):
        return str(self)

    def __str__(self):
        s = ''
        if self.last_name:
            s = self.last_name
            if self.first_name:
                s = '{} {}'.format(self.first_name, s)
        return s
