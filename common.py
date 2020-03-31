import pymongo
from datetime import datetime
import base64
import logging
import random
import mimetypes
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
