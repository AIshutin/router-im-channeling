#from telegram.client import Telegram
from telegram import Bot
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
import pydantic

CHANNEL = Channels.tg
API_ID = "1087174"
API_HASH = "3370ae6b2b06dad548626a0fdafc14dc"

FILE_REMOVE_DELAY = 60 * 3

class TgCredentials(pydantic.BaseModel):
    token: str
    name: str = Channels.tg

def send_message(message: Message, credentials: TgCredentials,
                    files_directory: Optional[str] = None):

    assert(credentials.token is not None and credentials.token != '')
    bot = Bot(credentials.token)
    chat_id = int(message.thread_id)

    if message.mtype == MessageType.text:
        bot.send_message(chat_id=chat_id,
                        text=message.text)
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

        caption = message.text
        if caption == '':
            caption = None

        if message.mtype == MessageType.image:
            bot.send_photo(chat_id=chat_id,
                           photo=open(fname, 'rb'),
                           caption=caption)
        elif message.mtype == MessageType.file:
            bot.send_document(chat_id=chat_id,
                              document=open(fname, 'rb'),
                              caption=caption)
        os.remove(fname)
    print('SENT')

def add_channel(credentials: TgCredentials):
    tail = gen_random_string()
    our_url = f'{BASE_URL}{CHANNEL}/{tail}'
    tg_url = f'https://api.telegram.org/bot{credentials.token}/setWebhook?url={our_url}'
    requests.get(tg_url).raise_for_status()
    return tail

def remove_channel(credentials: TgCredentials):
    tg_url = f'https://api.telegram.org/bot{credentials.token}/deleteWebhook'
    resp = requests.get(tg_url)
    resp.raise_for_status()
    resp = resp.json()
    if not resp['result']:
        print(resp)
        raise AssertionError
