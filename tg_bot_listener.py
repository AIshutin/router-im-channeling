import requests
import random
import os
import logging
from datetime import datetime
from common import *
import copy

CHANNEL = 'tg_bot'
logger = logging.Logger('logger')
logger.setLevel(logging.DEBUG)

def run(request):
    req = request.get_json()
    path = request.path
    tail = parse_path(path)[-1]
    result = channels.find_one({'webhook_token': tail})
    if result is None:
        return 'Bad token'
    channel_id = result['_id']
    print(req)
    if 'message' in req:
        message = req['message']
        thread_id = str(message['chat']['id'])
        user = message.get('from', {})
        author = user.get('username', 'TelegramUser')
        author_name = user.get('first_name') + \
                    ' ' + user.get('last_name', '')
        author_type = 'user'
        timestamp = get_server_timestamp()
        logger.debug(timestamp, message.get('date')*1000)
        msg = { 'mtype': 'message',
                'text': message.get('text'),
                'author': author,
                'author_name': author_name,
                'author_type': author_type,
                'thread_id': thread_id,
                'channel': CHANNEL,
                'channel_id': str(result['_id']),
                'timestamp': message.get('date')*1000,
                'server_timestamp': timestamp,
                'original_ids': [str(message['message_id'])]
             }

        logger.debug(msg)
        caption = message.get('caption', '')

        token = result['credentials']['token']
        attachments = None
        for att in ['audio', 'document', 'voice', 'video', 'photo']:
            if att not in message:
                continue
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
            logging.debug(resp)

            file_path = resp['file_path']
            name = file_path.split('/')[-1]

            url = f'https://api.telegram.org/file/bot{token}/{file_path}'
            resp = requests.get(url, allow_redirects=True)
            fpath = f'/tmp/{gen_random_string()}.{file_format}'
            with open(fpath, 'wb') as file:
                file.write(resp.content)
            content = get_b64_file(fpath)
            os.remove(fpath)

            mtype = 'file' if att != 'photo' else 'image'
            if attachments is None:
                attachments = []
            attachments.append({'type': mtype, 'content': content, 'caption': caption, 'name': name})
        msg['attachments'] = attachments

        if 'reply_to_message' in message:
            id = str(message['reply_to_message']['message_id'])
            logging.debug(f'original reply id: {id}')
            our_id = messages.find_one({'channel': CHANNEL, 'original_ids': id})
            if our_id is not None:
                msg['reply_to'] = str(our_id['_id'])

        if 'forward_from' in message:
            forwarded = copy.deepcopy(msg)
            forwarded.pop('thread_id')
            forwarded.pop('channel_id')
            forwarded.pop('reply_to', None)
            msg['text'] = '.'
            msg.pop('attachments', None)
            msg['forwarded'] = [forwarded]
        add_new_message(msg)
    return 'Ok'

request_json_example = {'update_id': 116115482,
                        'message': {
                            'message_id': 335,
                            'from': {
                                'id': 438162308,
                                'is_bot': False,
                                'first_name': 'Andrew',
                                'last_name': 'Ishutin',
                                'username': 'aishutin',
                                'language_code': 'en'
                                },
                            'chat': {
                                'id': 438162308,
                                'first_name': 'Andrew',
                                'last_name': 'Ishutin',
                                'username': 'aishutin',
                                'type': 'private'
                                },
                            'date': 1583417418,
                            'photo': [
                                {'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADbQADUp4DAAEYBA', 'file_unique_id': 'AQADzx3BDgAEUp4DAAE', 'file_size': 19245, 'width': 320, 'height': 169}, {'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADeAADU54DAAEYBA',
                                 'file_unique_id': 'AQADzx3BDgAEU54DAAE',
                                 'file_size': 60995,
                                 'width': 800,
                                 'height': 422},
                                {'file_id': 'AgACAgIAAxkBAAIBT15hCExgYu0Voc8I5C9xuqcrA7KGAAL6rTEbt2IIS45qW3TsdO97zx3BDgAEAQADAgADeQADUJ4DAAEYBA',
                                 'file_unique_id': 'AQADzx3BDgAEUJ4DAAE',
                                 'file_size': 67460,
                                 'width': 892,
                                 'height': 471}
                                 ]
                            }
                        }
