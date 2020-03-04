import requests
from argparse import ArgumentParser
import pymongo
import time

def prepare_mongo(myclient, workspace):
    for collection in ['configs', 'channels', 'messages']:
        myclient[workspace][collection].drop()

    myclient[workspace]['configs'].insert_one({'value': 0, 'name': 'last_message_id'})
    myclient[workspace]['messages'].create_index([('message_id', pymongo.ASCENDING)], unique=True)

parser = ArgumentParser()

parser.add_argument('--host', default="localhost")
parser.add_argument('--port', default=2000)
parser.add_argument('--live', default=5)

args = parser.parse_args()
url = f"http://{args.host}:{args.port}/"
live = int(args.live)

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)

workspace = 'dino_001'
prepare_mongo(myclient, workspace)

tg_credentials = {'name': 'tg',
                  'self_id': '801339101',
                  'token': '801339101:AAH7GQKB5-XK0czIV9U6GzkafkC1Hq25o0o'}
channel = 'tg'
resp = requests.post(f'{url}upsert_channel', json={'workspace': workspace,
                                                   'channel': channel,
                                                   'credentials': tg_credentials})
print(resp.status_code, resp.text)
resp.raise_for_status()

while live > 0:
    live -= 1
    last_mid = -1
    for msg in myclient[workspace]['messages'].find({}):
        if msg['message_id'] <= last_mid:
            continue
        last_mid = msg['message_id']
        print(msg)
        message = {'mtype': 'text', 'content': 'hello_world!',
                    'author': 'Bob', 'author_name': 'Bob Sandeson', 'author_type': 'agent',
                    'channel': channel, 'timestamp': 1}
        resp = requests.post(f'{url}send_message', json={'message': message,
                                                        'workspace': workspace,
                                                        'channel': channel})
        print(resp.text)
        resp.raise_for_status()
resp = requests.post(f'{url}remove_channel', json={'workspace': workspace,
                                                    'channel': channel})
print(resp.text)
