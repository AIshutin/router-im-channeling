import pymongo
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel, Field
import senderlib
from senderlib.tg import TgCredentials
from senderlib.fb import FbCredentials
from senderlib.common import Channels, Message
from bson.objectid import ObjectId

class CredentialsNotFound(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials not found"

class Id(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, ObjectId) and not isinstance(v, str):
            raise TypeError('ObjectId required')
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, schema):
        schema.update({
            'Title': 'MongoDB ObjectID',
            'type': 'string'
        })


MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)

TAIL_DB = 'tails'
TAIL_COLL = 'tails'

app = FastAPI()

def upsert_channel(workspace: str, channel: Channels, credentials):
    assert(credentials.name == channel)
    random_tail = senderlib.add_channel(channel, credentials)
    _id = myclient[workspace]['channels'].insert_one(credentials.dict()).inserted_id
    myclient[TAIL_DB][TAIL_COLL].insert_one({'_id': _id,
                                            'tail': random_tail,
                                            'workspace': workspace,
                                            'name': channel})
    return {'channel_id': str(_id)}

@app.post('/upsert_channel/tg/')
def upsert_tg(workspace: str = Body(..., embed=True),
              credentials: TgCredentials = Body(..., embed=True)):
    return upsert_channel(workspace, Channels.tg, credentials)

@app.post('/upsert_channel/fb/')
def upsert_fb(workspace: str = Body(..., embed=True),
              credentials: FbCredentials = Body(..., embed=True)):
    return upsert_channel(workspace, Channels.fb, credentials)

@app.post('/remove_channel')
def remove_channel(workspace: str = Body(..., embed=True),
                  channel_id: Id = Body(..., embed=True)):
    credentials = myclient[workspace]['channels'].find_one({'_id': channel_id})
    if credentials is None:
        raise CredentialsNotFound(channel)
    credentials.pop('_id')
    senderlib.remove_channel(channel, ChannelCredentials(**credentials))
    myclient[workspace]['channels'].remove({'_id': channel_id})
    myclient[TAIL_DB][TAIL_COLL].remove({'_id': channel_id})

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
    return senderlib.send_message(credentials['name'], message, credentials)
