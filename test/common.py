import os
import pytest
import logging
import base64
import copy
import requests
import inspect
import logging
import time

logging.basicConfig(level=logging.DEBUG)
API_URL = os.getenv('API_URL', "http://localhost:2000")
if API_URL[-1] == '/':
    API_URL = API_URL[:-1]

text_message = {'mtype': 'message',
                'text': 'hello_world!',
                'author': 'Bob',
                'author_name': 'Bob Sanderson',
                'author_type': 'agent',
                }
TG_DEFAULT_THREAD_ID = os.getenv('TG_DEFAULT_THREAD_ID', '438162308')


image_path = './kitty2.jpg'
image_message = {'mtype': 'message',
                'text': 'some text',
                'author': 'Bob',
                'author_name': 'Bob Sanderson',
                'author_type': 'agent',
                'attachments': [
                    {'type': 'image',
                     'content': base64.b64encode(open(image_path, 'rb').read()).decode("utf-8"),
                     'caption': 'some_caption',
                     'name': os.path.basename(image_path)
                    }
                ]}

doc_path = './sample_doc.txt'
doc_message = {'mtype': 'message',
                'text': 'some text',
                'author': 'Bob',
                'author_name': 'Bob Sanderson',
                'author_type': 'agent',
                'attachments': [
                    {'type': 'file',
                     'content': base64.b64encode(open(doc_path, 'rb').read()).decode("utf-8"),
                     'caption': 'some_caption',
                     'name': os.path.basename(doc_path)
                    }
                ]}

reply_text_message = copy.deepcopy(text_message)
reply_text_message['reply_to'] = -1

reply_image_message = copy.deepcopy(image_message)
reply_image_message['reply_to'] = -1

forward_text_message = copy.deepcopy(text_message)
forward_text_message['forwarded'] = [copy.deepcopy(forward_text_message)]

def get_mongo_pass():
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', '8jxIlp0znlJm8qhL')
    logging.info(f'{MONGO_PASSWORD} used as MONGO_PASSWORD')

def get_mongo_link():
    MONGO_LINK = os.getenv('MONGO_LINK', f'mongodb+srv://cerebra-autofaq:'
                                         f'{get_mongo_pass()}@testing-pjmjc.'
                                         'gcp.mongodb.net/test?retryWrites'
                                         '=true&w=majority')
    logging.info(f'{MONGO_LINK} used as MONGO_LINK')

class get_db_client():
    def __init__(self):
        self.client = None
    def __call__(self):
        if self.client is None:
            import pymongo
            self.client = pymongo.MongoClient(MONGO_LINK)
        return self.client

def clean_db():
    try:
        assert(os.getenv('MODE') == 'DEBUG')
        myclient = get_db_client()
        myclient.drop_database('SERVICE')
    except Exception as exp:
        logging.critical('!!! DO NOT CLEAN DB IN PRODUCTION !!!')
        logging.critical(exp)

def upsert_channel(channel, credentials):
    url = f"{API_URL}/upsert_channel/{channel}"
    resp = requests.post(url, json={'credentials': credentials}, timeout=60*3)
    assert(resp.status_code == 200)
    data = resp.json()
    assert('channel_id' in data and len(data['channel_id']) > 0)
    return data['channel_id']

def remove_channel(channel, credentials, channel_id=None):
    if channel_id is None:
        channel_id = upsert_channel(channel, credentials)
    url = f"{API_URL}/remove_channel"
    resp = requests.post(url, json={'channel_id': channel_id})
    assert(resp.status_code == 200)

def send_message(message):
    url = f"{API_URL}/send_message"
    resp = requests.post(url, json={'message': message})
    assert(resp.status_code == 200)
    data =resp.json()
    assert('id' in data and len(data['id']) != 0)
    assert('original_ids' in data)
    assert('server_timestamp' in data and data['server_timestamp'] > 1e12)
    return data

class SenderClass:
    def __init__(self, channel, credentials, thread, message):
        self.channel = channel
        self.credentials = credentials
        self.thread = thread
        message = copy.deepcopy(message)
        message['thread_id'] = thread
        self.message = message
        self.was = False

    def __call__(self):
        assert(self.was is False)
        self.was = True
        channel_id = upsert_channel(self.channel, self.credentials)
        self.message['channel_id'] = channel_id
        REPLY_TO = 'reply_to' in self.message
        if REPLY_TO:
            self.message.pop('reply_to')
        FORWARDED = 'forwarded' in self.message and len(self.message['forwarded']) != 0
        if FORWARDED:
            msgs = copy.deepcopy(self.message['forwarded'])
            for i in range(len(msgs)):
                msgs[i]['channel_id'] = channel_id
                msgs[i]['thread_id'] = self.message['thread_id']
                upd = send_message(msgs[i])
                msgs[i].pop('channel_id')
                msgs[i].pop('thread_id')
                msgs[i]['id'] = upd['id']
                msgs[i]['original_ids'] = upd['original_ids']
                msgs[i]['timestamp'] = upd['timestamp']
                logging.debug(f"message for forwading: {msgs[i]}")
            self.message['forwarded'] = msgs
            logging.debug(f"final mesage: {self.message}")
        res = send_message(self.message)
        if REPLY_TO:
            self.message['reply_to'] = res['id']
            send_message(self.message)
        # remove_channel(self.channel, self.credentials, channel_id)

def _dirty_magic(self):
    """
    Discovers name of the method which ran it using pytest environment variable.
    Then runs SenderClass instance based on the name.

    Reason behind: Pytest can not run classes, only functions
    """
    name = os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]
    getattr(self, '_' + name)()

def add_attr_dict(clss, channel, credentials, thread, messages=[('text', text_message),
                                                             ('image', image_message),
                                                             ('reply_text', reply_text_message),
                                                             ('reply_image', reply_image_message),
                                                             ('forward_text', forward_text_message),
                                                             ('doc', doc_message)]):
    for message in messages:
        name = f"test_{channel}_{message[0]}"
        setattr(clss, '_' + name, SenderClass(channel, credentials, thread, message[-1]))
        setattr(clss, name, lambda self: _dirty_magic(self))
    return clss

def duplicate_upsertion(channel, credentials):
    resp1 = upsert_channel(channel, credentials)
    resp2 = upsert_channel(channel, credentials)
    assert(resp1 == resp2)
