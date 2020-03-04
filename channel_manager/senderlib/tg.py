from telegram.client import Telegram
from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL
import threading
import requests

CHANNEL = Channels.tg
API_ID = "1087174"
API_HASH = "3370ae6b2b06dad548626a0fdafc14dc"
FILE_REMOVE_DELAY = 60 * 1

def send_message(message: Message, credentials: ChannelCredentials,
                    files_directory: Optional[str] = None):

    if files_directory is None:
        files_directory = f'/tmp/{gen_random_string()}/'

    phone = None if len(credentials.phone) == 0 else credentials.phone
    token = None if len(credentials.token) == 0 else credentials.token

    print(credentials)

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

    if message.mtype == MessageType.text:
        tg.send_message(chat_id=int(message.thread_id),
                            text=message.content)
    elif message.mtype == MessageType.image or message.mtype == MessageType.file:
        file_content = message.content

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

        data = {
            '@type': 'sendMessage',
            'chat_id': message.thread_id,
            'input_message_content': cont,
        }

        result = tg._send_data(data)
        result.wait()

        threading.Thread(target=(lambda delay, fname: (time.sleep(delay), os.remove(fname))),
            args=(FILE_REMOVE_DELAY, fname)).start()
    tg.stop()
    os.remove(files_directory)

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
    if resp.text != 'True':
        print(resp.text)
        raise AssertionError
