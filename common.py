import pymongo
from datetime import datetime
import base64
import logging
import random
import os
import mimetypes
from senderlib.common import save_b64_to_file
logging.basicConfig(level=logging.DEBUG)

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)
channels = myclient['SERVICE']['channels']
messages = myclient['SERVICE']['messages']
IMGS_FORMATS = {'jpg', 'jpeg', 'png', 'svg', 'bmp'}

def get_b64_file(fpath):
    with open(fpath, "rb") as file:
        return base64.b64encode(file.read())

def get_mime_type(fpath):
    ctype, encoding = mimetypes.guess_type(fpath)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    return (maintype, subtype)

def parse_path(path):
    parts = path[1:].split('/')
    assert(len(parts) == 2 or len(parts) == 1)
    return parts

def get_message_id_by_original_id(original_id, thread_id):
    if original_id == '':
        return None
    for el in messages.find({'original_ids': str(original_id), 'thread_id': thread_id})\
                                             .sort([('server_timestamp', 1)]):
        return el['_id']

def add_new_message(message):
    return messages.insert_one(message).inserted_id

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

def get_server_timestamp():
    return int(datetime.timestamp(datetime.utcnow()) * 1000)

POLLING_TIME = int(os.getenv('POLLING_TIME', 60))
TIME_GAP = POLLING_TIME * 2
TIME_FIELD = 'webhook_token'

class ServerStyleProcesser:
    def __init__(self, channel, listener_class):
        self.channel = channel
        self.listener_class = listener_class

    def check_if_alive_and_update(self, cid):
        if channels.find_one({'_id': cid}) is None:
            logging.debug(f'channel {cid} was deleted')
            return False
        current_time = str(int(get_server_timestamp() + TIME_GAP)//1000)
        res = channels.update_one({'_id': cid}, {'$max': {TIME_FIELD: current_time}})
        if res.modified_count == 0:
            logging.debug(f"probably, we are not responsible for processing channel {cid}")
            res2 = channels.find_one({'_id': cid})
            logging.debug(f"upd_value: {current_time}; original_value: {res2[TIME_FIELD]}")
            return False
        return True

    def remove_channel(self, channel):
        self.channels2listeners.pop(channel['_id'], None)

    def add_new_channel(self, channel):
        self.channels2listeners[str(channel['_id'])] = self.listener_class(channel)

    def search_for_avaible_channels(self):
        current_time = str(int(get_server_timestamp()//1000))
        query = {TIME_FIELD: {'$lt': current_time},
                'channel_type': self.channel}
        for channel in channels.find(query):
            if len(self.channels2listeners) >= MAX_CHANNELS_PER_INSTANCE:
                break
            deadline = str(TIME_GAP + int(time.time()))
            self.add_new_channel(channel)

    def listen_to_new_channels(self, period=3):
        while time.sleep(period) is None:
            self.search_for_avaible_channels()
