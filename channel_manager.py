import pymongo
from fastapi import FastAPI, Query, Body, HTTPException
from pydantic import BaseModel, Field
import senderlib
from senderlib.fb import FbCredentials
from senderlib.vk import VkCredentials
from senderlib.common import Channels, Message, Id
from bson.objectid import ObjectId
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

class CredentialsNotFound(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials not found"

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)
channels = myclient['SERVICE']['channels']
messages = myclient['SERVICE']['messages']

app = FastAPI()

def upsert_channel(channel: Channels, credentials):
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

@app.post('/upsert_channel/tg_bot/')
def upsert_tg_bot(credentials: senderlib.tg_bot.TgCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.tg_bot, credentials)

@app.post('/upsert_channel/fb/')
def upsert_fb(credentials: FbCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.fb, credentials)

@app.post('/upsert_channel/vk/')
def upsert_fb(credentials: VkCredentials = Body(..., embed=True)):
    return upsert_channel(Channels.vk, credentials)

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
    credentials = channels.find_one({'_id': channel_id})
    if credentials is None:
        for el in channels.find({}):
            logging.debug(el)
        raise CredentialsNotFound(channel_id)
    channel = credentials['channel_type']
    credentials = credentials['credentials']

    message.channel = channel
    message.server_timestamp = message.timestamp = datetime.timestamp(datetime.utcnow())
    logging.debug(message.dict())

    replied = None
    if message.reply_to is not None and message.reply_to != -1:
        replied = messages.find_one({'message_id': message.reply_to})
        replied.pop('_id')
        logging.debug(replied)
        replied = Message(**replied)
        replied.channel = channel
    resp = senderlib.send_message(channel, message, credentials, replied=replied)
    logging.debug('IDs', resp)
    message.original_ids = resp
    return {'id': str(add_new_message(message.dict())), 'original_ids': message.original_ids,
            'service_timestamp': message.service_timestamp}
