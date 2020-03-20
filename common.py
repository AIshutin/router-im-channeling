import pymongo
from datetime import datetime
import base64

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)
channels = myclient['SERVICE']['channels']
messages = myclient['SERVICE']['messages']
IMGS_FORMATS = {'jpg', 'jpeg', 'png', 'svg', 'bmp'}

def get_b64_file(fpath):
    with open(fpath, "rb") as file:
        return base64.b64encode(file.read())

def parse_path(path):
    parts = path[1:].split('/')
    assert(len(parts) == 2 or len(parts) == 1)
    return parts

def add_new_message(message):
    return messages.insert_one(message).inserted_id

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

def get_server_timestamp():
    return datetime.timestamp(datetime.utcnow())
