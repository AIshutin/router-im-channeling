import pymongo
import base64
import requests
import random
import os

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)
CHANNEL = 'tg'
TAIL_DB = "tails"

IMGS_FORMATS = {'jpg', 'jpeg', 'png', 'svg', 'bmp'}

def get_b64_file(fpath):
    with open(fpath, "rb") as file:
        return base64.b64encode(file.read())

def parse_path(path):
    parts = path[1:].split('/')
    assert(len(parts) == 2 or len(parts) == 1)
    return parts

def get_new_id(workspace):
    max_id = myclient[workspace]['configs'].find_and_modify({'name': 'last_message_id'},
                                                {'$inc': {'value': 1}}, new=1)['value']
    return max_id

def add_new_message(workspace, message):
    message['message_id'] = get_new_id(workspace)
    myclient[workspace]['messages'].insert_one(message)

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

def run(request):
    req = request.get_json()
    path = request.path
    tail = parse_path(path)[-1]
    result = myclient[TAIL_DB][CHANNEL].find_one({'tail': tail})
    if result is None:
        return 'Bad tail'
    workspace = result['workspace']
    print(req)
    '''
    {'update_id': 116115482, 'message': {'message_id': 335, 'from': {'id': 438162308, 'is_bot': False, 'first_name': 'Andrew', 'last_name': 'Ishutin', 'username': 'aishutin', 'language_code': 'en'}, 'chat': {'id': 438162308, 'first_name': 'Andrew', 'last_name': 'Ishutin', 'username': 'aishutin', 'type': 'private'}, 'date': 1583417418, 'photo': [{'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADbQADUp4DAAEYBA', 'file_unique_id': 'AQADzx3BDgAEUp4DAAE', 'file_size': 19245, 'width': 320, 'height': 169}, {'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADeAADU54DAAEYBA', 'file_unique_id': 'AQADzx3BDgAEU54DAAE', 'file_size': 60995, 'width': 800, 'height': 422}, {'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADeQADUJ4DAAEYBA', 'file_unique_id': 'AQADzx3BDgAEUJ4DAAE', 'file_size': 67460, 'width': 892, 'height': 471}]}}
    '''
    if 'message' in req:
        message = req['message']
        thread_id = str(message['chat']['id'])
        user = message.get('from', {})
        author = user.get('username', 'TelegramUser')
        author_name = user.get('first_name') + \
                    ' ' + user.get('last_name', '')
        author_type = 'user'
        timestamp = message['date']
        if 'text' in message:
            msg = {'mtype': 'text',
                    'text': message['text'],
                    'author': author,
                    'author_name': author_name,
                    'author_type': author_type,
                    'thread_id': thread_id,
                    'channel': CHANNEL,
                    'timestamp': timestamp,
                    'original_id': str(message['message_id'])
                    }
            add_new_message(workspace, msg)
            return 'Ok'
        msg = {'mtype': 'file',
                'author': author,
                'author_name': author_name,
                'author_type': author_type,
                'thread_id': thread_id,
                'channel': CHANNEL,
                'timestamp': timestamp,
                'original_id': str(message['message_id'])
                }
        if 'caption' in message:
            msg['text'] = message['caption']

        token = None
        for att in ['audio', 'document', 'voice', 'video', 'photo']:
            if att not in message:
                continue
            if token is None:
                res = myclient[workspace]['channels'].find_one({'name': CHANNEL})
                token = res['token']

            if att != 'photo':
                file_id = message[att]['file_id']
                file_format = message[att]['mime_type'].split('/')[-1]
            else:
                mx = 0
                file_id = None
                file_format = None
                for el in message[att]:
                    sz = el['width'] * el['height']
                    if mx < sz:
                        mx = sz
                        file_id = el['file_id']
                        #file_format = el['mime_type'].split('/')[-1]
                if file_id is None:
                    continue
            url = f'https://api.telegram.org/bot{token}/getFile?file_id={file_id}'
            resp = requests.get(url).json()['result']
            print(resp)

            file_path = resp['file_path']
            file_format = file_path.split('/')[-1]

            if '.' not in file_format:
                file_format = ''
            else:
                file_format = file_format[file_format.find('.') + 1:]
            url = f'https://api.telegram.org/file/bot{token}/{file_path}'
            resp = requests.get(url, allow_redirects=True)
            fpath = f'/tmp/{gen_random_string()}.{file_format}'
            with open(fpath, 'wb') as file:
                file.write(resp.content)
            content = get_b64_file(fpath)
            os.remove(fpath)

            mtype = 'file' if att != 'photo' else 'image'
            msg['mtype'] = mtype
            msg['content'] = content
            msg['file_format'] = file_format

            add_new_message(workspace, msg)
            break
    return 'Ok'
