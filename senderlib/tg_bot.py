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
import logging
import shutil

CHANNEL = Channels.tg
API_ID = "1087174"
API_HASH = "3370ae6b2b06dad548626a0fdafc14dc"

FILE_REMOVE_DELAY = 60 * 3

class TgCredentials(pydantic.BaseModel):
    token: str

def send_message(message: Message, credentials: TgCredentials, replied=Optional[Message]):
    bot = Bot(credentials.token)
    chat_id = int(message.thread_id)
    original_ids = []
    if len(message.text) != 0:
        original_id =bot.send_message(chat_id=chat_id,
                                        text=message.text)['message_id']
        print(original_id)
        original_ids.append(str(original_id))
        #tg.send_message(chat_id=int(message.thread_id),
        #                    text=message.text).wait()
    if message.attachments is not None and len(message.attachments) != 0:
        for attachment in message.attachments:
            file_content = attachment.content
            caption = attachment.caption

            bytes = base64.b64decode(file_content)
            random_name = gen_random_string(30)
            fdir = f'/tmp/{random_name}'
            os.mkdir(fdir)
            fname = f'{fidr}/{attachment.name}'
            with open(fname, 'wb') as file:
                file.write(bytes)

            caption = message.text
            if caption == '':
                caption = None

            if message.mtype == MessageType.image:
                original_id = bot.send_photo(chat_id=chat_id,
                                            photo=open(fname, 'rb'),
                                            caption=caption)['message_id']
            elif message.mtype == MessageType.file:
                original_id = bot.send_document(chat_id=chat_id,
                                                document=open(fname, 'rb'),
                                                caption=caption)['message_id']
            shutil.rm_tree(fname)
            original_ids.append(original_id)
    logging.info('SENT')
    logging.debug(original_ids)
    return original_ids

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
        logging.debug(resp)
        raise AssertionError
