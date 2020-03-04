import pymongo
import base64
import requests
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
    message.message_id = get_new_id(workspace)
    myclient[workspace]['messages'].insert_one(message)

def run(request):
    req = request.get_json()
    path = request.path
    tail = parse_path(path)[-1]
    result = myclient[TAIL_DB][CHANNEL].find_one({'tail': tail})
    if result is None:
        return 'Bad tail'
    workspace = result['workspace']
    print(req)

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
                    'content': message['text'],
                    'author': author,
                    'author_name': author_name,
                    'author_type': author_type,
                    'thread_id': thread_id,
                    'channel': CHANNEL,
                    'timestamp': timestamp,
                    }
            add_new_message(workspace, msg)
        if 'caption' in message:
            msg = {'mtype': 'text',
                    'content': message['caption'],
                    'author': author,
                    'author_name': author_name,
                    'author_type': author_type,
                    'thread_id': thread_id,
                    'channel': CHANNEL,
                    'timestamp': timestamp,
                    }
            add_new_message(workspace, msg)

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
                        file_format = el['mime_type'].split('/')[-1]
                if file_id is None:
                    continue
            url = f'https://api.telegram.org/bot{token}/getFile?file_id={file_id}'
            file_path = requests.get(url).json()['file_path']
            url = f'https://api.telegram.org/file/bot{token}/{file_path}'
            resp = requests.get(url, allow_redirects=True)
            fpath = f'/tmp/{gen_random_string()}.{file_format}'
            with open(fpath, 'wb') as file:
                file.write(resp.content)
            content = get_b64_file(fpath)
            os.remove(fpath)

            mtype = 'file' if att != 'photo' else 'image'
            msg = {'mtype': mtype,
                    'content': content,
                    'author': author,
                    'author_name': author_name,
                    'author_type': author_type,
                    'thread_id': thread_id,
                    'channel': CHANNEL,
                    'timestamp': timestamp,
                    'file_format': file_format
                }
            add_new_message(workspace, msg)
