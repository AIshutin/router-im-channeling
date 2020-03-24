import os
import pytest
import logging
import base64
import copy
import requests
import inspect
API_URL = os.getenv('API_URL', "http://localhost:2000")

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
    resp = requests.post(url, json={'credentials': credentials})
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
    assert('original_ids' in data and len(data['original_ids']) != 0)
    assert('server_timestamp' in data and data['server_timestamp'] > 1e12)
    return data

def _test_send_message(channel, credentials, thread, message):
    message = copy.deepcopy(message)
    channel_id = upsert_channel(channel, credentials)
    message['channel_id'] = channel_id
    message['thread_id'] = thread
    send_message(message)
    remove_channel(channel_id)

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
        send_message(self.message)
        remove_channel(self.channel, self.credentials, channel_id)

def _dirty_func(self):
    name = os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]
    getattr(self, '_' + name)()

def add_attr_dict(clss, channel, credentials, thread, messages=[('text', text_message),
                                                             ('image', image_message)]):
    for message in messages:
        name = f"test_{channel}_{message[0]}"
        setattr(clss, '_' + name, SenderClass(channel, credentials, thread, message[-1]))
        setattr(clss, name, lambda self: _dirty_func(self))
    return clss

def duplicate_upsertion(channel, credentials):
    resp1 = upsert_channel(channel, credentials)
    resp2 = upsert_channel(channel, credentials)
    assert(resp1 == resp2)
