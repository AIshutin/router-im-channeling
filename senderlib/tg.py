from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    AttachmentType, get_utc_timestamp
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
import time

CHANNEL = 'tg'

class TgCredentials(pydantic.BaseModel):
    phone: str
    db: Optional[str]
    link: str
    self_id: str
    password: Optional[str]

def send_message(message: Message, credentials: TgCredentials, \
        replied=Optional[Message], specific: dict=None):
    logging.debug(f"server url {specific['url']}")
    msg_dict = message.dict()
    msg_dict['channel_id'] = str(msg_dict['channel_id'])
    if 'reply_to' in msg_dict and msg_dict['reply_to'] is not None:
        msg_dict['reply_to'] = str(msg_dict['reply_to'])
    if 'forwarded' in msg_dict and msg_dict['forwarded'] is not None:
        for i in range(len(msg_dict['forwarded'])):
            msg_dict['forwarded'][i]['id'] = str(msg_dict['forwarded'][i]['id'])
    resp = requests.post(specific['url'], json={'message': msg_dict})
    logging.debug(f"server response {resp.text}")
    resp.raise_for_status()

    return resp.json()['original_ids']

def add_channel(credentials: TgCredentials):
    return str(get_utc_timestamp() - 10**6)

def remove_channel(credentials: TgCredentials):
    return
