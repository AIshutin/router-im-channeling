import pymongo
from fastapi import FastAPI, Query, Body, HTTPException
from pydantic import BaseModel, Field
import senderlib
from senderlib.fb import FbCredentials
from senderlib.vk import VkCredentials
from senderlib.mail import EmailCredentials
from senderlib.common import Channels, Message, Id
from bson.objectid import ObjectId
import logging
from datetime import datetime
import os
import time
logging.debug('This is debug message')

class CredentialsNotFound(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials not found"

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = os.getenv('MONGO_LINK', f'mongodb+srv://cerebra-autofaq:'
                                     f'{MONGO_PASSWORD}@testing-pjmjc.'
                                     'gcp.mongodb.net/test?retryWrites'
                                     '=true&w=majority')
logging.info(f'{MONGO_LINK} used as MONGO_LINK')

myclient = pymongo.MongoClient(MONGO_LINK)
channels = myclient['SERVICE']['channels']
messages = myclient['SERVICE']['messages']

app = FastAPI()

def upsert_channel(channel: Channels, credentials):
    credentials_dict = credentials.dict()
    res = channels.find_one({'channel_type': channel, 'credentials': credentials_dict})
    if res is not None:
        return {'channel_id': str(res['_id'])}
    webhook_token = senderlib.add_channel(channel, credentials)
    logging.debug(webhook_token)

    common_credentials = senderlib.Credentials(channel_type=channel,
                                               credentials=credentials,
                                               webhook_token=webhook_token)
    _id = channels.insert_one(common_credentials.dict()).inserted_id
    logging.debug(_id)
    for el in channels.find({}):
        logging.debug(el)
    return {'channel_id': str(_id)}

def upsert_channel_long_action(channel: Channels, credentials, delay=100):
    search_dict = credentials.dict()
    if channel == Channels.tg:
        search_dict.pop('db', None)
        search_dict.pop('link', None)
    for key in list(search_dict.keys()):
        search_dict[f'credentials.{key}'] = search_dict.pop(key)
    search_dict['channel_type'] = channel
    res = channels.find_one(search_dict)
    if res is not None:
        return {'channel_id': str(res['_id'])}
    str_timestamp = senderlib.add_channel(channel, credentials)
    logging.debug(str_timestamp)

    common_credentials = senderlib.Credentials(channel_type=channel,
                                               credentials=credentials,
                                               timestamp=str_timestamp,
                                               webhook_token="")
    logging.info(common_credentials.dict())
    _id = channels.insert_one(common_credentials.dict()).inserted_id
    time.sleep(delay)
    res = channels.find_one({'_id': _id})
    if res is None:
        raise HTTPException(status_code=500, detail='channel was removed before confirmation')
    if res['webhook_token'] == str_timestamp:
        raise HTTPException(status_code=500, detail='channel was not accepted. Check credentials.')
    return {'channel_id': str(_id)}

@app.post('/upsert_channel/tg_bot/')
def upsert_tg_bot(credentials: senderlib.tg_bot.TgCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.tg_bot, credentials)

@app.post('/upsert_channel/fb/')
def upsert_fb(credentials: FbCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.fb, credentials)

@app.post('/upsert_channel/vk/')
def upsert_fb(credentials: VkCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.vk, credentials)

@app.post('/upsert_channel/email/')
def upsert_fb(credentials: EmailCredentials = Body(..., embed=True)):
    return upsert_channel_long_action(Channels.email, credentials, 20)

@app.post('/upsert_channel/tg')
def upsert_tg(credentials: senderlib.tg.TgCredentials = Body(..., embed=True)):
    result = upsert_channel_long_action(Channels.tg, credentials, 60)
    return result

@app.post('/_tg_get_code/{dc_id}')
def _tg_get_code(dc_id: int):
    if dc_id != 0:
        return {'code': 5 * str(dc_id)}
    return {'code': input('Enter code: ')}

@app.post('/remove_channel')
def remove_channel(channel_id: Id = Body(..., embed=True)):
    credentials = channels.find_one({'_id': channel_id})
    if credentials is None:
        raise CredentialsNotFound(channel)
    senderlib.remove_channel(credentials['channel_type'], credentials['credentials'])
    channels.remove({'_id': channel_id})

def add_new_message(message: dict):
    message.pop('_id', None)
    _id = messages.insert_one(message).inserted_id
    return _id

class FieldIsNotNone(Exception):
    def __init__(self, field):
        self.field = field
    def __str__(self):
        return f"{self.field} must be none when sending messages to a server."

@app.post('/send_message')
def send_message(message: Message = Body(..., embed=True)):
    if message.original_ids is not None:
        raise HTTPException(status_code=400, detail=str(FieldIsNotNone('original_ids')))
    if message.server_timestamp is not None:
        raise HTTPException(status_code=400, detail=str(FieldIsNotNone('server_timestamp')))
    if message.timestamp is not None:
        raise HTTPException(status_code=400, detail=str(FieldIsNotNone('timestamp')))
    if message.id is not None:
        raise HTTPException(status_code=400, detail=str(FieldIsNotNone('id')))

    channel_id = message.channel_id
    logging.debug(type(channel_id))
    channel_obj = channels.find_one({'_id': channel_id})
    if channel_obj is None:
        for el in channels.find({}):
            logging.debug(el)
        raise CredentialsNotFound(channel_id)
    channel = channel_obj['channel_type']
    credentials = channel_obj['credentials']

    message.channel = channel
    message.server_timestamp = message.timestamp = int(datetime.timestamp(datetime.utcnow()) * 1000)
    logging.debug(message.dict())

    replied = None
    if message.reply_to is not None:
        logging.debug(message.reply_to)
        replied = messages.find_one({'_id': message.reply_to})
        replied['id'] = replied['_id']
        replied.pop('_id')
        logging.debug(replied)
        replied = Message(**replied)
        replied.channel = channel

    platform_specific = None
    if message.channel == Channels.tg:
        platform_specific = {'url': channel_obj['webhook_token']}

    resp = senderlib.send_message(channel, message, credentials, replied=replied, specific=platform_specific)
    message.original_ids = resp
    id = str(add_new_message(message.dict()))

    return {'id': id, 'original_ids': message.original_ids,
            'server_timestamp': message.server_timestamp, 'timestamp': message.timestamp}
