import pymongo
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel, Field
import senderlib
from senderlib.tg import TgCredentials
from senderlib.fb import FbCredentials
from senderlib.vk import VkCredentials
from senderlib.common import Channels, Message, Id
from bson.objectid import ObjectId

class CredentialsNotFound(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials not found"


MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)

TAIL_DB = 'tails'
TAIL_COLL = 'tails'

app = FastAPI()

def upsert_channel(workspace: str, channel: Channels, credentials):
    assert(credentials.name == channel)
    random_tail = senderlib.add_channel(channel, credentials)
    print(random_tail)
    _id = myclient[workspace]['channels'].insert_one(credentials.dict()).inserted_id
    myclient[TAIL_DB][TAIL_COLL].insert_one({'_id': _id,
                                            'tail': random_tail,
                                            'workspace': workspace,
                                            'name': channel})
    print(_id)
    for el in myclient[TAIL_DB][TAIL_COLL].find({}):
        print(el)
    return {'channel_id': str(_id)}

@app.post('/upsert_channel/tg/')
def upsert_tg(workspace: str = Body(..., embed=True),
              credentials: TgCredentials = Body(..., embed=True)):
    return upsert_channel(workspace, Channels.tg, credentials)

@app.post('/upsert_channel/fb/')
def upsert_fb(workspace: str = Body(..., embed=True),
              credentials: FbCredentials = Body(..., embed=True)):
    return upsert_channel(workspace, Channels.fb, credentials)

@app.post('/upsert_channel/vk/')
def upsert_fb(workspace: str = Body(..., embed=True),
              credentials: VkCredentials = Body(..., embed=True)):
    return upsert_channel(workspace, Channels.vk, credentials)

@app.post('/remove_channel')
def remove_channel(workspace: str = Body(..., embed=True),
                  channel_id: Id = Body(..., embed=True)):
    credentials = myclient[workspace]['channels'].find_one({'_id': channel_id})
    if credentials is None:
        raise CredentialsNotFound(channel)
    credentials.pop('_id')
    senderlib.remove_channel(credentials['name'], credentials)
    myclient[workspace]['channels'].remove({'_id': channel_id})
    myclient[TAIL_DB][TAIL_COLL].remove({'_id': channel_id})

def get_new_id(workspace: str):
    max_id = myclient[workspace]['configs'].find_and_modify({'name': 'last_message_id'},
                                                {'$inc': {'value': 1}}, new=1)['value']
    return max_id

def add_new_message(workspace: str, message: dict):
    if message['message_id'] == -1:
        message['message_id'] = get_new_id(workspace)
    myclient[workspace]['messages'].insert_one(message)
    return message['message_id']

@app.post('/send_message')
def send_message(workspace: str = Body(..., embed=True),
                 channel_id: Id = Body(..., embed=True),
                 message: Message = Body(..., embed=True)):
    print(type(channel_id))
    credentials = myclient[workspace]['channels'].find_one({'_id': channel_id})
    if credentials is None:
        for el in myclient[workspace]['channels'].find({}):
            print(el)
        raise CredentialsNotFound(channel_id)
    credentials.pop('_id')
    message.message_id = get_new_id(workspace)
    print(message.dict())
    replied = None
    if message.reply_to is not None and message.reply_to != -1:
        replied = myclient[workspace]['messages'].find_one({'message_id': message.reply_to})
        replied.pop('_id')
        print(replied)
        replied = Message(**replied)
    resp = senderlib.send_message(credentials['name'], message, credentials, replied=replied)
    print('ID', resp)
    message.original_id = str(resp)
    '''dct = message.dict()
    print(dct)
    for el in resp:
        dct[el] = resp[el]'''
    add_new_message(workspace, message.dict())
