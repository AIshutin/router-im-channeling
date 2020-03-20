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
from common import *
import logging

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
            for el in myclient[workspace]['messages'].find({'original_id': str(reply_to), 'thread_id': thread_id})\
                                                     .sort([('message_id', 1)]):
                reply_to = el['message_id']
                was = True
                print(el, reply_to)
                break
            logging.debug(was, reply_to)

            if not was:
                reply_to = -1

    forwarded = []
    for el in fwd_messages:
        if channel_id == '':
            break
        msgs = process_vk_message(el, workspace, self_id, '', main_thread_id)
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
    logging.debug(message)
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
        logging.info(url, caption)

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

    logging.debug(msg, len(text))
    res.append(msg)

    for i in range(len(res)):
        if 'message_id' not in res[i]:
            orid = res[i]['original_id']
            res[i]['message_id'] = get_message_id_by_original_id(orid, main_thread_id, workspace)

    return res

def run(request):
    json_data = request.get_json(force=True)
    if json_data['secret'] != SECRET_VK_KEY:
        logging.debug(json_data['secret'])
        return BadRequest(description='bad secret')
    path = request.path
    webhook_token = parse_path(path)[-1]
    result = channels.find_one({'webhook_token': webhook_token})
    if result is None:
        raise NotFound(description="Bad token")
    _id = result['_id']

    if json_data['type'] == 'confirmation':
        group_id = str(json_data['group_id'])
        logging.debug(group_id, _id, type(_id))
        credentials = result['credentials']
        if credentials['self_id'] != group_id:
            raise BadRequest(description=f"{group_id} is not found")
        else:
            token = credentials['token']
            vk = vk_api.VkApi(token=token).get_api()
            code = vk.groups.getCallbackConfirmationCode(group_id=int(group_id))
            logging.info('code', code)
            code = code['code']
            logging.info(group_id, code)
            return code
    elif json_data['type'] == 'message_new':
        logging.debug(json_data)
        message = json_data['object']['message']
        group_id = str(json_data['group_id'])
        msgs = process_vk_message(message, workspace, group_id, str(result['_id']))
        assert(len(msgs) == 1)
        add_new_message(msgs[0])
    elif json_data['type'] == 'message_edit':
        logging.debug(json_data)
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
        assert(len(msgs) == 1)
        add_new_message(msgs[0])
    return 'ok'
