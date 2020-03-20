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
import mimetypes

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
TAIL_DB = 'tails'
TAIL_COLL = 'tails'
CHANNEL = 'fb'
myclient = pymongo.MongoClient(MONGO_LINK)
SECRET_VK_KEY = '9YAVEQAraTr4pClNDjvg'

def get_new_id(workspace, cnt=1):
    max_id = myclient[workspace]['configs'].find_and_modify({'name': 'last_message_id'},
                                                {'$inc': {'value': cnt}}, new=1)['value']
    return max_id

def add_new_messages(workspace, messages):
    if len(messages) == 0:
        return
    last_id = get_new_id(workspace, len(messages))
    for i in range(1, len(messages) + 1):
        messages[-i]['message_id'] = last_id
        last_id -= 1
    myclient[workspace]['messages'].insert_many(messages)

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

def get_message_id_by_original_id(original_id, thread_id, workspace):
    if original_id == '':
        return -1
    ans = -1
    for el in myclient[workspace]['messages'].find({'original_id': str(original_id), 'thread_id': thread_id})\
                                             .sort([('message_id', 1)]):
        ans = el['message_id']
        break
    return ans

def process_vk_message(message, workspace: str, self_id: str, channel_id: str="", main_thread_id: str=""):
    original_id = str(message.get('id', ''))
    timestamp = message['date']
    thread_id = str(message['from_id'])
    if main_thread_id == '':
        main_thread_id = thread_id
    text = message.get('text', '')
    reply_to = message.get('reply_message', {}).get('id', -1)
    fwd_messages = message.get('fwd_messages', [])

    if channel_id == '':
        reply_to = -1
    if reply_to != -1:
            was = False
            #for el in myclient[workspace]['messages'].find({}):
            #    print(el)
            for el in myclient[workspace]['messages'].find({'original_id': str(reply_to), 'thread_id': thread_id})\
                                                     .sort([('message_id', 1)]):
                reply_to = el['message_id']
                was = True
                print(el, reply_to)
                break
            print('ln104', was, reply_to)

            if not was:
                reply_to = -1

    forwarded = []
    for el in fwd_messages:
        if channel_id == '':
            break
        #try:
        msgs = process_vk_message(el, workspace, self_id, '', main_thread_id)
        #except Exception as exp:
        #    print(exp, el)
        #    msgs = []
        forwarded += msgs
    sender_type = 'user'

    if str(message['from_id']) == self_id:
        sender_type = 'agent'
        author_name = '??Agent??'
        author = author_name
    else:
        sender_type = 'user'
        author_name = f'VkUser{thread_id}'
        author = f'VkUser{thread_id}'

    msg = {
            'text': text,
            'author': author,
            'author_name': author_name,
            'author_type': sender_type,
            'channel': CHANNEL,
            'timestamp': timestamp,
            'original_id': original_id,
        }
    if channel_id != '':
        msg['thread_id'] = thread_id
        msg['forwarded'] = forwarded
        msg['channel_id'] = channel_id
        msg['message_id'] = -1
        msg['reply_to'] = reply_to

    was = False
    print(message)
    res = []
    for attachment in message.get('attachments', []):
        ftype = 'file'
        if attachment['type'] == 'photo':
            ftype = 'image'
            file = attachment[attachment['type']]
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
            caption = attachment[attachment['type']].get('title', '')
        print(url, caption)

        r = requests.get(url)
        fpath = f'/tmp/{gen_random_string(30)}'
        with open(fpath, 'wb') as f:
            f.write(r.content)

        content = get_b64_file(fpath)
        os.remove(fpath)

        file_name = urlparse(url).path
        file_name = file_name[file_name.rfind('/') + 1:]
        attachment = {'type': ftype, 'content': content,
                      'name': file_name, 'caption': caption}

        if 'attachments' not in msg:
            msg['attachments'] = attachment
        msg['attachments'].append(attachment)

    print(msg, len(text))
    res.append(msg)

    for i in range(len(res)):
        if 'message_id' not in res[i]:
            orid = res[i]['original_id']
            res[i]['message_id'] = get_message_id_by_original_id(orid, main_thread_id, workspace)

    return res

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
        group_id = str(json_data['group_id'])
        msgs = process_vk_message(message, workspace, group_id, str(result['_id']))
        add_new_messages(workspace, msgs)
        return "ok"
    elif json_data['type'] == 'message_edit':
        print(json_data)
        message = json_data['object']
        group_id = str(json_data['group_id'])
        msgs = process_vk_message(message, workspace, group_id, str(result['_id']))

        if len(msgs) == 0:
            return 'ok'

        orid = msgs[0].get('original_id', '')
        cnt = 1
        for el in myclient[workspace]['messages'].find({'original_id': orid}).sort([('mversion', -1)]):
            cnt = el['mversion'] + 1
        for i in range(len(msgs)):
            msgs[i]['mversion'] = cnt
        add_new_messages(workspace, msgs)
        return 'ok'
