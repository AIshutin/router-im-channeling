from python_telegram.client import Telegram
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

CHANNEL = 'tg'
API_ID = os.getenv('API_ID', "1087174")
API_HASH = os.getenv('API_HASH', "3370ae6b2b06dad548626a0fdafc14dc")
logging.info(f'{API_ID} used as API_ID for Telegram')
logging.info(f'{API_HASH} used as API_HASH for Telegram')

class TgCredentials(pydantic.BaseModel):
    phone: str
    db: Optional[str]
    link: str
    self_id: str
    password: Optional[str]

def send_message(message: Message, credentials: TgCredentials, replied=Optional[Message]):
    return []

def add_channel(credentials: TgCredentials):
    fdir = f'/tmp/{gen_random_string(30)}'
    tg = Telegram(
        api_id=API_HASH,
        api_hash=API_HASH,
        phone=credentials.phone,  # you can pass 'bot_token' instead
        database_encryption_key=API_HASH,
        auth_credentials=credentials
    )
    tg.login()
    # if this is the first run, library needs to preload all chats
    # otherwise the message will not be sent
    result = tg.get_chats()
    result.wait()
    del tg
    fpath = f'/tmp/{gen_random_string()}'
    shutil.make_archive(fdir, 'zip', fpath)
    content = get_b64_file(fpath)
    shutil.rmtree(fdir)
    credentials.db = content
    return ""

def remove_channel(credentials: TgCredentials):
    return
