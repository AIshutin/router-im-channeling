from telegram import Bot
from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    AttachmentType
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

CHANNEL = Channels.tg_bot

FILE_REMOVE_DELAY = 60 * 3

class TgCredentials(pydantic.BaseModel):
    token: str

def send_message(message: Message, credentials: TgCredentials, \
        replied=Optional[Message], specific: Optional[dict]=None):
    bot = Bot(credentials.token)
    chat_id = int(message.thread_id)
    original_ids = []
    text = message.text
    reply_to_message = None
    if replied is not None:
        reply_to_message = int(replied.original_ids[0])
    msg_to_forward = []
    if message.forwarded is not None:
        for el in message.forwarded:
            if el.id is None:
                text = fallback_forward(text) + text
            else:
                msg_to_forward += el.original_ids


    if len(text) != 0:
        original_id =bot.send_message(chat_id=chat_id,
                                        text=message.text,
                                        reply_to_message_id=reply_to_message)['message_id']
        print(original_id)
        original_ids.append(str(original_id))
        reply_to_message = None
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
            fname = f'{fdir}/{attachment.name}'
            with open(fname, 'wb') as file:
                file.write(bytes)

            caption = attachment.caption
            if caption == '':
                caption = None

            if attachment.type == AttachmentType.image:
                original_id = bot.send_photo(chat_id=chat_id,
                                            photo=open(fname, 'rb'),
                                            reply_to_message_id=reply_to_message,
                                            caption=caption)['message_id']
            elif attachment.type == AttachmentType.file:
                original_id = bot.send_document(chat_id=chat_id,
                                                document=open(fname, 'rb'),
                                                caption=caption,
                                                reply_to_message_id=reply_to_message)['message_id']
            shutil.rmtree(fdir)
            reply_to_message = None
            original_ids.append(original_id)
    for el in msg_to_forward:
        original_ids.append(bot.forward_message(chat_id, chat_id, int(el))['message_id'])
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
