import requests
from argparse import ArgumentParser
import pymongo
import time
import base64

def prepare_mongo(myclient):
    myclient.drop_database('SERVICE')

parser = ArgumentParser()

parser.add_argument('--host', default="localhost")
parser.add_argument('--port', default=2000)
parser.add_argument('--live', default=5)
parser.add_argument('--type', default='t')
parser.add_argument('--channel', default='tg_bot')
parser.add_argument('--reply', default=None)
parser.add_argument('--without_upserting', default=None)
parser.add_argument('--forward', default=None)
args = parser.parse_args()
url = f"http://{args.host}:{args.port}/"
live = int(args.live)
reply = args.reply
forward = args.forward
without_upserting = args.without_upserting

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)

prepare_mongo(myclient)

tg_credentials = {'token': '801339101:AAH7GQKB5-XK0czIV9U6GzkafkC1Hq25o0o'} # 'self_id': '801339101'
fb_credentials = {'self_id': '101962504709802',
                  'token': 'EAAIrF0hyVy0BALNlqxTKXsUC2YUnT4GzDMdG6LsYmVIO0y1ocBNcWHzrs26GYWDQr8m5A9aMMjGZBqzYtywW8JmWuAi0DGhGJGeeZA0kz5XCC6u2ptiRPaqfYbu9MRrZCn34JHWAbuFokGJ3E4Fpdjg1ERrSO2M2gkhzoSonwZDZD'}
vk_credentials = {'code': '4c3e7bcf', 'token': '1895dbfc845d148eaf334224f661aa14d3cd641badb9eda096370d58efeca73e10d9a4040c9827d54c699', 'self_id': "190503682"}
channel = args.channel
all_credentials = {'tg_bot': tg_credentials, 'fb': fb_credentials, 'vk': vk_credentials}
credentials = all_credentials[channel]
if without_upserting is None:
    resp = requests.post(f'{url}upsert_channel/{channel}', json={'credentials': credentials})
    print(resp.status_code, resp.text)
    resp.raise_for_status()
    channel_id = resp.json()['channel_id']
else:
    channel_id = None

message = {'mtype': 'message', 'text': 'hello_world!',
            'author': 'Bob', 'author_name': 'Bob Sanderson', 'author_type': 'agent',
            'channel': channel}

img_file = open("kitty2.jpg", "rb")
img_message = {'mtype': 'message', 'content': base64.b64encode(img_file.read()).decode("utf-8"),
            'file_format': 'jpg', 'author': 'Bob', 'text': 'Look and smile',
            'author_name': 'Bob Sanderson', 'author_type': 'agent',
            'channel': channel}

doc_file = open("requirements.txt", "rb")

doc_message = {'mtype': 'message', 'content': base64.b64encode(doc_file.read()),
                'file_format': 'txt', 'author': 'Bob', 'author_name': 'Bob Sanderson',
                'author_type': 'agent', 'channel': channel}

msg_type = args.type
msg = {'f': doc_message, 'i': img_message, 't': message}[msg_type[0]]

def send_message(message):
    if 'thread_id' not in message:
        if message['channel'] == 'tg':
            message['thread_id'] = '438162308'
        if message['channel'] == 'fb':
            message['thread_id'] = '2673203139464950'

    resp = requests.post(f'{url}send_message', json={'message': message})
    print(resp.text)
    resp.raise_for_status()
    return resp

def loop(message, live=live):
    last_timestamp = -1
    while live != 0:
        live -= 1

        for msg in myclient['SERVICE']['messages'].find({}):

            if msg['server_timestamp'] <= last_timestamp:
                continue
            print(msg, last_timestamp)
            last_timestamp = msg['server_timestamp']
            if msg['author_type'] == 'agent':
                continue
            message['thread_id'] = msg['thread_id']
            message['channel_id'] = msg['channel_id']
            message['text'] = f"Your text length is {len(msg['text'])}"

            if reply is not None:
                message['reply_to'] = last_mid

            if forward is not None:
                import copy
                msg2 = copy.deepcopy(msg)
                msg2.pop('forwarded', 0)
                msg2.pop('reply_to', 0)
                msg2.pop('channel_id', 0)
                msg2.pop('thread_id', 0)
                msg2.pop('_id', 0)
                message['forwarded'] = [msg2]
            if 'content' in message:
                print(type(message['content']))
            print(message)
            send_message(message)
            print('\n\n')
        time.sleep(5)

loop(msg)

if without_upserting is None:
    resp = requests.post(f'{url}remove_channel', json={'workspace': workspace,
                                                    'channel_id': channel_id})
    print(resp.text)
