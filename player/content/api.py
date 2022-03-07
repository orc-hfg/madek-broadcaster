import asyncio
import collections
import tempfile

import pyglet
import simplejson as json
import urllib

import aiohttp
import sys
from uritemplate import expand

from content.apidata import PeopleData, KeywordData, MetaDatum
from content.collections import CollectionData
from content.mediaentry import *

PathIdType = collections.namedtuple('PathIdType', 'path, id, type')


class ApiClient(object):
    """
    ApiClient
    """

    HTTP_STATUS_CODES_TO_RETRY = [500, 502, 503, 504]

    RESOURCE_PATHS = {
        'media-entry': '/api/media-entries/{}',
        'collection': '/api/collections/{}',
        'person': '/api/people/{}',
        'keyword': '/api/keywords/{}'
    }

    @classmethod
    def complete(cls, path_=None, id_=None, type_=None):
        """
        Expects either path or id and type and returns id and path as a tuple.
        """
        if id_ and type_:
            path_ = ApiClient.id_to_path(id_, type_)
        elif path_:
            id_, type_ = ApiClient.path_to_id(path_)
        return PathIdType(path_, id_, type_)

    @classmethod
    def id_to_path(cls, id_, type_):
        """
        Expects an id and a resource type (media-entry, collection, person, keyword).
        """
        if type_ in ApiClient.RESOURCE_PATHS:
            path_template = ApiClient.RESOURCE_PATHS[type_]
            if path_template:
                return path_template.format(id_)
        return None

    @classmethod
    def path_to_id(cls, path_):
        """
        Expects an api path and returns the id and type of the resource.
        """
        for k, v in ApiClient.RESOURCE_PATHS.items():
            v = ''.join(v.split('{}'))
            if path_.find(v) > -1:
                type_ = k
                # TODO: find actual id
        return path_.split('/').pop(), type_

    def __init__(self, server_: str, user_: str, pass_: str):
        """
        :param server_: URL of the server, like 'http://medienarchiv.zhdk.ch'
        :param user_: username of API-client
        :param pass_: password of API-client
        """
        super(ApiClient, self).__init__()
        self.__auth = aiohttp.BasicAuth(user_, pass_)
        self.__server = server_
        self.__header = {
            'content-type': 'application/json-roa+json', 'accept': 'application/json-roa+json'}
        self.debug = False
        self.__request_counter = 0
        self.__session = None
        self.__semaphore = asyncio.Semaphore(1000)
        self.__connector = None
        # this parameter prevents that all media entry are requested
        self.__max_media_entries = 100
        self.__loop = None
        self.__future = None
        self.__active = False

    def start_session(self):
        """
        Initiates an asynchronous session.
        """
        self.__active = True
        self.__request_counter = 0
        self.__loop = asyncio.get_event_loop()
        self.__connector = aiohttp.TCPConnector(loop=self.__loop, limit=20)
        if not self.__session or self.__session.closed:
            self.__session = aiohttp.ClientSession(connector=self.__connector, loop=self.__loop, auth=self.__auth,
                                                   headers=self.__header, conn_timeout=None)
        # limit the number of parallel requests
        return self.__loop

    def complete_session(self):
        """
        Completes an asynchronous session.
        """
        print('{} requests'.format(self.__request_counter))
        self.__active = False
        self.__session.close()
        self.__session = None

    @property
    def session_active(self):
        return self.__active

    async def send_request(self, path_,
                    retries=3,
                    interval=0.9,
                    back_off=1.5,
                    read_timeout=15.9,
                    http_status_codes_to_retry=HTTP_STATUS_CODES_TO_RETRY):
        """
        This internal function handles all requests to the server and returns
        either the entire JSON or None.
        """
        back_off_interval = interval
        raised_exc = None
        attempt = 0
        if self.debug:
            print('send_request - {}'.format(path_))
        if retries == -1:  # -1 means retry indefinitely
            attempt = -1
        elif retries == 0:  # Zero means don't retry
            attempt = 1
        else:  # any other value means retry N times
            attempt = retries + 1
        self.__request_counter += 1
        url = '{}{}'.format(self.__server, path_)
        if self.__session.closed and self.debug:
            print('Session closed!')
            return None
        while attempt != 0:
            if raised_exc:
                print('caught "{}" url:{} remaining tries {}, sleeping {} secs'.format(raised_exc,
                                                                                       url, attempt, back_off_interval))
                await asyncio.sleep(back_off_interval)
                # bump interval for the next possible attempt
                back_off_interval = back_off_interval * back_off
            try:
                with aiohttp.Timeout(timeout=read_timeout):
                    async with getattr(self.__session, 'get')(url) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                            except json.JSONDecodeError as exc:
                                print('failed to decode response code:{} url:{} error:{} response:{}'.format(
                                    response.status, url, exc,
                                    response.reason)
                                )
                                raise aiohttp.errors.HttpProcessingError(
                                    code=response.status, message=exc.msg)
                            else:
                                if self.debug:
                                    print('... url:{} code:{} response:{}'.format(url, response.status, response.reason))
                                raised_exc = None
                                return data
                        elif response.status in http_status_codes_to_retry:
                            print('received invalid response code:{} url:{} response:{}'.format(
                                response.status, url, response.reason))
                            raise aiohttp.errors.HttpProcessingError(
                                code=response.status, message=response.reason)
                        else:
                            try:
                                data = await response.json(encoding='utf-8')
                            except json.JSONDecodeError as exc:
                                print('failed to decode response code:%s url:%s error:%s response:%s'.format(
                                    response.status, url,
                                    exc, response.reason))
                                raise FailedRequest(
                                    code=response.status, message=exc,
                                    raised=exc.__class__.__name__, url=url)
                            else:
                                print('received {} for {}'.format(data, url))
                                print(data['errors'][0]['detail'])
                                raised_exc = None
                                return data
            except (aiohttp.errors.ClientResponseError,
                    aiohttp.errors.ClientRequestError,
                    aiohttp.errors.ClientOSError,
                    aiohttp.errors.ClientDisconnectedError,
                    aiohttp.errors.ClientTimeoutError,
                    asyncio.TimeoutError,
                    aiohttp.errors.HttpProcessingError) as exc:
                try:
                    code = exc.code
                except AttributeError:
                    code = ''
                raised_exc = FailedRequest(code=code, message=exc, url=url,
                                           raised=exc.__class__.__name__)
            else:
                raised_exc = None
                break
            attempt -= 1
        if raised_exc:
            raise raised_exc


    def get_auth_info(self):
        # simply requests authentication data from the server
        # used for testing only
        self.__loop = asyncio.get_event_loop()
        self.__session = aiohttp.ClientSession(auth=self.__auth, headers=self.__header, loop=self.__loop)
        auth_info_json = self.__loop.run_until_complete(self.send_request('/api/auth-info'))
        self.__loop.close()
        self.__session.close()

    async def load_collection(self, id_):
        """
        Requires a collection uuid.
        :param id_: UUID, e.g. '187af3e9-1c81-44bc-98e7-e38733d7a730'
        :type id_: str
        :return Collection
        """
        path = ApiClient.complete(None, id_, 'collection').path
        j = await self.send_request(path)
        if j:
            c = CollectionData.get_instance(j['id'], j)
            roa = j['_json-roa']

            # get collection meta data
            path = roa['relations']['meta-data']['href'].split('{')[0]
            await self.handle_meta_data(await self.send_request(path))

            # get media - and make sure that the client has the correct permissions
            params = urllib.parse.urlencode({'me_get_metadata_and_previews': 'true'})
            path = roa['relations']['media-entries']['href'].split('{')[0] + '&' + params
            for m in await self.get_media_entries(path):
                if m:
                    c.add_media_entry(m)

                    # TODO: get sub-collections

                    # TODO: get filter-sets

        return c

    async def get_media_entries(self, path_, limit_=None, meta_data_white_list_=None, preload_media_=False):
        """
        Requests media entries based on a complete api-path.
        """
        media_entries = []
        tasks = []
        if limit_:
            limit = limit_
        else:
            limit = self.__max_media_entries
        ready = False
        while not ready:
            j = await self.send_request(path_)
            # find entries and start all requests
            roa = j['_json-roa']
            for i in roa['collection']['relations'].items():
                if i[1]['name'] == 'Media-Entry':
                    path_ = i[1]['href']
                    task = asyncio.ensure_future(self.get_media_entry(path_,
                                                                      meta_data_white_list_=meta_data_white_list_,
                                                                      preload_media_=preload_media_))
                    tasks.append(task)
                if tasks.__len__() >= limit:
                    ready = True
                    break
            # find next page
            if not ready and 'next' in roa['collection']:
                path_ = roa['collection']['next']['href']
            else:
                ready = True

        for r in await asyncio.gather(*tasks):
            if r:
                media_entries.append(r)

        return media_entries

    async def get_media_entry(self, path_=None, id_=None, meta_data_white_list_=None, preload_media_=False):
        cr = ApiClient.complete(path_, id_, 'media-entry')
        j = await self.send_request(cr.path)
        if j:
            m = MediaEntryData.get_instance(cr.id, j)
            roa = j['_json-roa']
            if 'relations' in roa:
                if 'meta-data' in roa['relations']:
                    p = expand(roa['relations']['meta-data']['href'], {'?meta_keys': ''})
                    meta_data = Config().meta_data_white_list
                    if meta_data_white_list_:
                        meta_data = list(set(meta_data_white_list_) | set(Config.META_DATA_MINIMUM))
                    params = urllib.parse.urlencode({'meta_keys': meta_data})
                    p = p + '?' + params.replace('+','').replace('%27','%22')
                    await self.handle_meta_data(await self.send_request(p))
                if 'media-file' in roa['relations']:
                    mf = await self.get_media_file(roa['relations']['media-file']['href'])
                    if mf:
                        m.set_file_data(mf)
                        if preload_media_:
                            await self.cache_media_file(m)
                    else:
                        # a media entry without media files is invalid
                        print('No MediaFile for MediaEntry {}'.format(m.id))
                        m = None
                    pass
        return m

    async def handle_meta_data(self, json_):
        """
        Takes meta data json either for collection or media entry and requests actual values.
        """
        # Belongs to Collection or Media Entry?
        if 'collection_id' in json_:
            a = CollectionData.find(json_['collection_id'])
        elif 'media_entry_id' in json_:
            a = MediaEntryData.find(json_['media_entry_id'])
        roa = json_['_json-roa']
        # Has values to request?
        if a and 'collection' in roa and 'relations' in roa['collection']:
            tasks = []
            for m in roa['collection']['relations'].items():
                k = m[0]
                task = asyncio.ensure_future(self.get_meta_datum(m[1]['href']))
                tasks.append(task)
            for r in await asyncio.gather(*tasks):
                if type(r) is MetaDatum:
                    a.set_meta_datum(r)

    async def get_meta_datum(self, path_):
        """
        Returns a single meta-datum as name tuple KeyValue with field name and value.
        Value can be string or list with PeopleData or KeywordData
        """
        j = await self.send_request(path_)
        if j:
            m = MetaDatum(j)
            if type(j['value']) is str:
                return m
            elif type(j['value']) is list:
                # this assumes that all items in the list belong to the same meta key
                roa = j['_json-roa']
                tasks = []
                for i in roa['collection']['relations'].items():
                    if i[1]['name'] == 'Person':
                        task = asyncio.ensure_future(self.get_person(i[1]['href']))
                        tasks.append(task)
                    elif i[1]['name'] == 'Keyword':
                        task = asyncio.ensure_future(self.get_keyword(i[1]['href']))
                        tasks.append(task)
                for r in await asyncio.gather(*tasks):
                    m.add_value(r)
                return m
            else:
                print('unrecognized data type: ' + str(type(j['value'])))
        return None

    async def get_person(self, path_=None, id_=None):
        """
        Returns a person based on either api path or an id.
        """
        cr = ApiClient.complete(path_, id_, 'person')
        # Persons are not updated if they were already requested
        p = PeopleData.find(cr.id)
        if not p:
            # TODO: Create instance before sending request and not on response.
            j = await self.send_request(cr.path)
            if j:
                return PeopleData.get_instance(j)
        return None

    async def get_keyword(self, path_=None, id_=None):
        """
        Returns a keyword base of either api path or keyword id.
        """
        cr = ApiClient.complete(path_, id_, 'keyword')
        # Keywords are not updated if they were already requested
        k = KeywordData.find(cr.id)
        if not k:
            j = await self.send_request(cr.path)
            if j:
                return KeywordData.get_instance(j)
        return k

    async def get_media_file(self, path):
        """
        :param path:
        :return:
        """
        j = await self.send_request(path)
        if j:
            mf = MediaFileData(self.__server, j)
            roa = j['_json-roa']
            tasks = []
            # look for previews
            for r in j['previews']:
                task = asyncio.ensure_future(self.get_preview(roa['collection']['relations'][r['id']]['href']))
                tasks.append(task)
            for p in await asyncio.gather( * tasks):
                mf.add_preview(p)
            if mf.get_preview():
                return mf
        return None

    async def cache_media_file(self, media_entry_):
        # TODO: this is not asynched yet
        file = MediaFile(media_entry_)

    async def get_preview(self, path):
        j = await self.send_request(path)
        if j:
            return PreviewData(self.__server, j)
        return None


class MediaEntryParams():
    def __init__(self, json_:dict={}):
        self.order = json_.get('order', 'desc')
        self.public_get_metadata_and_previews = json_.get('public_get_metadata_and_previews', True)
        self.public_get_full_size = json_.get('public_get_full_size')
        self.me_get_metadata_and_previews = json_.get('me_get_metadata_and_previews')
        self.me_get_full_size = json_.get('me_get_metadata_and_previews')
        self.filter_by = json_.get('filter_by')
        self.collection_id = json_.get('collection_id')

    @property
    def data(self):
        d = {}
        if self.order:
            d['order'] = self.order
        if self.public_get_metadata_and_previews:
            d['public_get_metadata_and_previews'] = self.public_get_metadata_and_previews
        if self.public_get_full_size:
            d['public_get_full_size'] = self.public_get_full_size
        if self.me_get_metadata_and_previews:
            d['me_get_metadata_and_previews'] = self.me_get_metadata_and_previews
        if self.me_get_full_size:
            d['me_get_full_size'] = self.me_get_full_size
        if self.filter_by:
            d['filter_by'] = self.filter_by
        if self.collection_id:
            d['collection_id'] = self.collection_id
        return d

    @property
    def url(self):
        if not self.data:
            return ''
        return '/api/media-entries/?{}'.format(urllib.parse.urlencode(self.data).replace('%27','%22').replace('True','true').replace('False','false'))

    @property
    def web_url(self):
        f = {
            'list[filter]': self.filter_by,
            'list[show_filter]': 'true',
            'list[page]': 1,
            'list[per_page]': 12,
            'list[order]': 'created_at DESC',
            'list[layout]': 'grid'
        }
        return '/entries?{}'.format(urllib.parse.urlencode(f).replace('%27','%22').replace('True','true').replace('False','false'))

    def __str__(self):
        return self.url


class FailedRequest(Exception):
    """
    A wrapper of all possible exception during a HTTP request
    """
    code = 0
    message = ''
    url = ''
    raised = ''

    def __init__(self, *, raised='', message='', code='', url=''):
        self.raised = raised
        self.message = message
        self.code = code
        self.url = url

        super().__init__("code:{c} url={u} message={m} raised={r}".format(
            c=self.code, u=self.url, m=self.message, r=self.raised))
