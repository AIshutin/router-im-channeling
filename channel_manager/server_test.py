import requests
from argparse import ArgumentParser
import pymongo
import time
import base64

def prepare_mongo(myclient, workspace):
    for collection in ['configs', 'channels', 'messages']:
        myclient[workspace][collection].drop()

    myclient[workspace]['configs'].insert_one({'value': 0, 'name': 'last_message_id'})
    myclient[workspace]['messages'].create_index([('message_id', pymongo.ASCENDING)], unique=True)
    myclient['tails']['fb'].drop()

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

tg_credentials = {'token': '801339101:AAH7GQKB5-XK0czIV9U6GzkafkC1Hq25o0o'} # 'self_id': '801339101'
fb_credentials = {'self_id': '101962504709802',
                  'token': 'EAAIrF0hyVy0BALNlqxTKXsUC2YUnT4GzDMdG6LsYmVIO0y1ocBNcWHzrs26GYWDQr8m5A9aMMjGZBqzYtywW8JmWuAi0DGhGJGeeZA0kz5XCC6u2ptiRPaqfYbu9MRrZCn34JHWAbuFokGJ3E4Fpdjg1ERrSO2M2gkhzoSonwZDZD'}
vk_credentials = {'code': '4c3e7bcf', 'token': '1895dbfc845d148eaf334224f661aa14d3cd641badb9eda096370d58efeca73e10d9a4040c9827d54c699', 'self_id': "190503682"}
channel = 'vk'
all_credentials = {'tg': tg_credentials, 'fb': fb_credentials, 'vk': vk_credentials}
credentials = all_credentials[channel]
resp = requests.post(f'{url}upsert_channel/{channel}', json={'workspace': workspace,
                                                   'credentials': credentials})
print(resp.status_code, resp.text)
resp.raise_for_status()
channel_id = resp.json()['channel_id']

message = {'mtype': 'text', 'text': 'hello_world!',
            'author': 'Bob', 'author_name': 'Bob Sanderson', 'author_type': 'agent',
            'channel': channel, 'timestamp': 1}

img_file = open("kitty2.jpg", "rb")
img_message = {'mtype': 'image', 'content': base64.b64encode(img_file.read()).decode("utf-8"),
            'file_format': 'jpg', 'author': 'Bob', 'text': 'Look and smile',
            'author_name': 'Bob Sanderson', 'author_type': 'agent',
            'channel': channel, 'timestamp': 1}

doc_file = open("requirements.txt", "rb")

doc_message = {'mtype': 'file', 'content': base64.b64encode(doc_file.read()),
                'file_format': 'txt', 'author': 'Bob', 'author_name': 'Bob Sanderson',
                'author_type': 'agent', 'channel': channel, 'timestamp': 1}

def send_message(message):
    if 'thread_id' not in message:
        if message['channel'] == 'tg':
            message['thread_id'] = '438162308'
        if message['channel'] == 'fb':
            message['thread_id'] = '2673203139464950'

    resp = requests.post(f'{url}send_message', json={'message': message,
                                                    'workspace': workspace,
                                                    'channel_id': channel_id})
    print(resp.text)
    resp.raise_for_status()
    return resp


def loop(message, live=live):
    last_mid = -1
    while live != 0:
        live -= 1

        for msg in myclient[workspace]['messages'].find({}):
            if msg['message_id'] <= last_mid:
                continue
            last_mid = msg['message_id']
            if msg['author_type'] == 'agent':
                continue
            print(msg, last_mid)
            message['thread_id'] = msg['thread_id']
            message['channel_id'] = msg['channel_id']
            if message['mtype'] == 'text':
                message['text'] = f"Your text length is {len(msg['text'])}"
            if 'content' in message:
                print(type(message['content']))

            send_message(message)
        time.sleep(5)

loop(img_message)

resp = requests.post(f'{url}remove_channel', json={'workspace': workspace,
                                                    'channel_id': channel_id})
print(resp.text)
