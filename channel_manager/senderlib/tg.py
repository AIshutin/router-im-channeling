from telegram.client import Telegram
from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type
import threading
import requests
import os
import time
import shutil
import requests
import base64

CHANNEL = Channels.tg
API_ID = "1087174"
API_HASH = "3370ae6b2b06dad548626a0fdafc14dc"

FILE_REMOVE_DELAY = 60 * 3

def send_message(message: Message, credentials: ChannelCredentials,
                    files_directory: Optional[str] = None):

    if message.mtype == MessageType.text:
        requests.post(f'https://api.telegram.org/bot{credentials.token}/sendMessage',
                json={'chat_id': int(message.thread_id),
                        'text': message.text})
        #tg.send_message(chat_id=int(message.thread_id),
        #                    text=message.text).wait()
    elif message.mtype == MessageType.image or message.mtype == MessageType.file:
        file_content = message.content
        caption = message.text

        bytes = base64.b64decode(file_content)
        random_name = gen_random_string(30)
        fname = f'/tmp/{random_name}.{message.file_format}'
        with open(fname, 'wb') as file:
            file.write(bytes)

        url = f'https://api.telegram.org/bot{credentials.token}/sendImage'
        parameter = 'photo'
        if message.mtype == MessageType.file:
            url = f'https://api.telegram.org/bot{credentials.token}/sendDocument'
            parameter = 'document'

        # ('spam.txt', open('spam.txt', 'rb'), 'text/plain')
        multipart = (fname, open(fname, 'rb'), guess_mime(fname))

        requests.post(url, json={parameter: multipart,
                                'chat_id': int(message.thread_id)})
        os.remove(fname)
    print('SENT')

def add_channel(credentials: ChannelCredentials):
    tail = gen_random_string()
    our_url = f'{BASE_URL}{CHANNEL}/{tail}'
    tg_url = f'https://api.telegram.org/bot{credentials.token}/setWebhook?url={our_url}'
    requests.get(tg_url).raise_for_status()
    return tail

def remove_channel(credentials: ChannelCredentials):
    tg_url = f'https://api.telegram.org/bot{credentials.token}/deleteWebhook'
    resp = requests.get(tg_url)
    resp.raise_for_status()
    resp = resp.json()
    if not resp['result']:
        print(resp)
        raise AssertionError
