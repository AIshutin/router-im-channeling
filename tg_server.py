from senderlib import python_telegram
from common import *
from zipfile import ZipFile
import os

CHANNEL = 'tg'
API_ID = os.getenv('API_ID', "1087174")
API_HASH = os.getenv('API_HASH', "3370ae6b2b06dad548626a0fdafc14dc")
logging.info(f'{API_ID} used as API_ID for Telegram')
logging.info(f'{API_HASH} used as API_HASH for Telegram')


class TgListener:
    def __init__(self, channel):
        self.channel = channel
        self.credentials = channel['credentials']
        self.fdir = f'/tmp/{gen_random_string()}'
        fdir2 = f'/tmp/{gen_random_string()}/'
        os.mkdir(self.fdir)
        os.mkdir(fdir2)
        fpath2 = fdir2 + 'db.zip'
        save_b64_to_file(self.credentials['db'], fpath2)
        with ZipFile(fpath2, 'r') as zipObj:
            zipObj.extractall(path=self.fdir)

        self.tg = Telegram(
            api_id=API_ID,
            api_hash=API_HASH,
            phone=self.credentials['phone'],  # you can pass 'bot_token' instead
            database_encryption_key=self.credentials['phone'],
            files_directory=self.fdir,
            auth_credentials=self.credentials
        )
        self.tg.login()
        result = self.tg.get_chats()
        result.wait()

        self.tg.add_message_handler(self.handle_message)
        self.tg.add_update_handler('updateFile', self.handle_file)

    def handle_file(self, update):

        pass

    def handle_message(self, update):
        chat_id = update['message']['chat_id']
        author = str(update['message']['sender_user_id'])
        if author == self.credentials['self_id']:
            return
        user_info = self.tg.get_user(int(author))
        logging.debug(f"User_info: {user_info}")
        name = user_info.get('first_name', author) + ' ' + user.get('last_name', '')
        logging.debug(f"name: {name}")
        if update['message']['content']['@type'] == "messageDocument":
            pass
        else:
            message_content = update['message']['content'].get('text', {})
            message_text = message_content.get('text', '')

            message = {
                'mtype': 'message',
                'text': message_text,
                'author': str(author),
                'author_name': name,
                'author_type': 'user',
                'thread_id': str(chat_id),
                'channel': CHANNEL,
                'timestamp': int(update['message']['date'])*1000,
                'server_timestamp': get_server_timestamp(),
            }

            add_new_message(message)

    def __del__(self):
        # maybe, it should update db in credentials
        shutil.rmtree(self.fdir)
processer = ServerStyleProcesser(CHANNEL, TgListener)
processer.listen_to_new_channels()
