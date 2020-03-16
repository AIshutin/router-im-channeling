import time
import requests
import threading
import time
from itertools import chain
import imaplib
import datetime
from enum import Enum
import json
from werkzeug.exceptions import HTTPException, BadRequest, NotFound
import base64
import pymongo
from urllib.parse import urlparse
import random
import os
import vk_api

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
TAIL_DB = 'tails'
TAIL_COLL = 'tails'
CHANNEL = 'fb'
myclient = pymongo.MongoClient(MONGO_LINK)
SECRET_VK_KEY = '9YAVEQAraTr4pClNDjvg'

def get_new_id(workspace):
    max_id = myclient[workspace]['configs'].find_and_modify({'name': 'last_message_id'},
                                                {'$inc': {'value': 1}}, new=1)['value']
    return max_id

def add_new_message(workspace, message):
    message['message_id'] = get_new_id(workspace)
    myclient[workspace]['messages'].insert_one(message)

def get_b64_file(fpath):
    with open(fpath, "rb") as file:
        return base64.b64encode(file.read())

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

def parse_path(path):
    parts = path[1:].split('/')
    assert(len(parts) == 2 or len(parts) == 1)
    return parts

def run(request):
    json_data = request.get_json(force=True)
    if json_data['secret'] != SECRET_VK_KEY:
        print(json_data['secret'])
        return "bad request"
    path = request.path
    tail = parse_path(path)[-1]
    print('TAIL', tail)
    result = myclient[TAIL_DB][TAIL_COLL].find_one({'tail': tail})
    if result is None:
        for el in myclient[TAIL_DB][TAIL_COLL].find({}):
            print(el)
        raise NotFound(description="Bad tail")
    workspace = result['workspace']
    _id = result['_id']
    if json_data['type'] == 'confirmation':
        group_id = str(json_data['group_id'])
        print(group_id, _id, type(_id))
        for el in myclient[workspace]['channels'].find({}):
            print(el)
        credentials = myclient[workspace]['channels'].find_one({'_id': _id})
        if credentials['self_id'] != group_id:
            print(credentials)
            raise BadRequest(description=f"{group_id} is not found")
        else:
            token = credentials['token']
            vk = vk_api.VkApi(token=token).get_api()
            #time.sleep(2)
            code = vk.groups.getCallbackConfirmationCode(group_id=int(group_id))
            print(code)
            code = code['code']
            #code = credentials['code']
            print(group_id, code)
            return code
    elif json_data['type'] == 'message_new':
        print(json_data)
        message = json_data['object']['message']
        original_id = str(message['id'])
        timestamp = message['date']
        thread_id = str(message['from_id'])
        group_id = str(json_data['group_id'])
        text = message.get('text', '')
        reply_to = message.get('reply_message', {}).get('id', -1)
        print('reply_to', reply_to)
        if reply_to != -1:
            was = False
            for el in myclient[workspace]['messages'].find({}):
                print(el)
            for el in myclient[workspace]['messages'].find({'original_id': str(reply_to), 'thread_id': thread_id})\
                                                     .sort([('message_id', 1)]):
                reply_to = el['message_id']
                was = True
                print(el, reply_to)
                break
            print('ln104', was, reply_to)

            if not was:
                reply_to = -1

        msg = {
                'mtype': 'text',
                'text': text,
                'author': f'VkUser{thread_id}',
                'author_name': f'VkUser{thread_id}',
                'author_type': 'user',
                'thread_id': thread_id,
                'channel': CHANNEL,
                'channel_id': str(result['_id']),
                'timestamp': timestamp,
                'message_id': -1,
                'reply_to': reply_to,
                'original_id': original_id
            }
        was = False
        print(message)
        for attachment in message.get('attachments', []):
            mtype = 'file'
            if attachment['type'] == 'photo':
                mtype = 'image'
                file =attachment[attachment['type']]
                caption = file.get('caption', '')
                url = None
                mx_sz = 0
                for el in file['sizes']:
                    curr_sz = el['width'] * el['height']
                    if curr_sz > mx_sz:
                        mx_sz = curr_sz
                        url = el['url']
                if url is None:
                    continue
            else:
                url = attachment[attachment['type']]['url']
            print(url)
            r = requests.get(url)
            fpath = f'/tmp/{gen_random_string(30)}'
            with open(fpath, 'wb') as f:
                f.write(r.content)

            content = get_b64_file(fpath)
            os.remove(fpath)

            msg['content'] = content
            fb_file_name = urlparse(url).path
            file_format = fb_file_name[fb_file_name.rfind('/') + 1:]
            print(file_format)
            if '.' in file_format:
                file_format = file_format[file_format.find('.') + 1:]
            else:
                file_format = ''
            msg['file_format'] = file_format
            msg['mtype'] = mtype

            print(msg)
            add_new_message(workspace, msg) # warning
            was = True
        print(was, len(text))
        if not was and len(text) != 0:
            add_new_message(workspace, msg)

        return "ok"
