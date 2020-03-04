import pymongo
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel, Field
import senderlib
from senderlib.common import Channels, ChannelCredentials, Message

class CredentialsNotFound(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials not found"

class CredentialsExist(Exception):
    def __init__(self, name: Channels):
        self.name = name
    def __str__(self):
        return f"{self.name} credentials already exist"

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)

TAIL_DB = "tails"

app = FastAPI()

@app.post('/upsert_channel')
def upsert_channel(workspace: str = Body(..., embed=True),
                channel: Channels = Body(..., embed=True),
                credentials: ChannelCredentials = Body(..., embed=True)):
    if myclient[workspace]['channels'].find_one({'name': channel}) is not None:
        raise CredentialsExist
    random_tail = senderlib.add_channel(channel, credentials)
    myclient[TAIL_DB][channel].insert_one({'tail': random_tail, 'workspace': workspace})

@app.post('/remove_channel')
def remove_channel(workspace: str = Body(..., embed=True),
                    channel: Channels = Body(..., embed=True)):
    credentials = myclient[workspace]['channels'].find_one({'name': channel})
    if credentials is None:
        raise CredentialsNotFound(channel)
    senderlib.remove_channel(channel, credentials)
    myclient[workspace]['channels'].remove({'name': channel})
    myclient[TAIL_DB][channel].remove({'workspace': workspace})

@app.post('/send_message')
def send_message(workspace: str = Body(..., embed=True),
                channel: Channels = Body(..., embed=True),
                message: Message = Body(..., embed=True)):

    credentials = myclient[workspace]['channels'].find_one({'name': channel})
    if credentials is None:
        raise CredentialsNotFound(channel)
    credentials.pop('_id')
    return senderlib.send_message(channel, message, ChannelCredentials(**credentials))
