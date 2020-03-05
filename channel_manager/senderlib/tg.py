from telegram.client import Telegram
from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType
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

    if files_directory is None:
        files_directory = f'/tmp/{gen_random_string()}/'

    try:
        os.makedirs(files_directory)
    except:
        pass

    phone = None if len(credentials.phone) == 0 else credentials.phone
    token = None if len(credentials.token) == 0 else credentials.token

    print(credentials)
    print(phone, token)
    tg = Telegram(
        api_id=API_ID,
        api_hash=API_HASH,
        phone=phone,
        bot_token=token,
        database_encryption_key=SECRET_INTERNAL_KEY,
        files_directory=files_directory
    )
    tg.login()
    result = tg.get_chats()
    result.wait()

    print('Logged in')

    if message.mtype == MessageType.text:
        #requests.post(f'https://api.telegram.org/bot{credentials.token}/sendMessage',
        #        json={'chat_id': int(message.thread_id),
        #                'text': message.content})
        tg.send_message(chat_id=int(message.thread_id),
                            text=message.text).wait()
        print('SENT')
    elif message.mtype == MessageType.image or message.mtype == MessageType.file:
        file_content = message.content
        caption = message.text

        bytes = base64.b64decode(file_content)
        random_name = gen_random_string(30)
        fname = f'/tmp/{random_name}.{message.file_format}'
        with open(fname, 'wb') as file:
            file.write(bytes)

        cont = {'@type': 'inputMessageDocument',
        'document': {'@type': 'inputFileLocal', 'path': fname}}

        if message.mtype == MessageType.file:
            cont = {'@type': 'inputMessageDocument',
                'document': {'@type': 'inputFileLocal', 'path': fname}}

        if caption is not None and len(caption) != 0:
            cont['caption'] = {'@type': 'formattedText',
                                'text': caption}

        data = {
            '@type': 'sendMessage',
            'chat_id': message.thread_id,
            'input_message_content': cont,
        }

        print(data)

        result = tg._send_data(data)
        result.wait()

        threading.Thread(target=(lambda delay, fname: (time.sleep(delay), os.remove(fname))),
            args=(FILE_REMOVE_DELAY, fname), daemon=True).start()

    threading.Thread(target=(lambda delay, files_directory: (time.sleep(delay), tg.stop(),
                                                    shutil.rmtree(files_directory))),
                    args=(FILE_REMOVE_DELAY, files_directory), daemon=True).start()

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
