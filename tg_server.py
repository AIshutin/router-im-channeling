import pyrogram
from common import *
from zipfile import ZipFile
import os
import sys
import io
import logging
import requests
import time
import threading
import shutil
import pyrohacks
logging.basicConfig(level=logging.DEBUG)
pyrogram.Client.authorize = pyrohacks.custom_authorize
pyrogram.Client.idle = pyrohacks.idle

CHANNEL = 'tg'
API_ID = os.getenv('API_ID', "1087174")
API_HASH = os.getenv('API_HASH', "3370ae6b2b06dad548626a0fdafc14dc")
logging.info(f'{API_ID} used as API_ID for Telegram')
logging.info(f'{API_HASH} used as API_HASH for Telegram')

class TgListener:
    def full_init(self):
        # reserve this channel for us
        processer.check_if_alive_and_update(self.channel['_id'])
        INIT_SESSION = False
        if self.credentials.get('db', None) is None or True:
            INIT_SESSION = True
            logging.debug('initializing new session..')
        else:
            fdir2 = f'/tmp/{gen_random_string()}/'
            os.mkdir(fdir2)
            fpath2 = fdir2 + 'db.tar'
            save_b64_to_file(self.credentials['db'], fpath2)
            shutil.unpack_archive(fpath2, extract_dir=self.fdir)
            shutil.rmtree(fdir2)

        test_mode = False
        if self.credentials['link'] == 'http://localhost:2000/_tg_get_code/2' or True:
            test_mode = True
        print(test_mode)
        app = pyrogram.Client("Router.im server", api_id=API_ID,
                                                  api_hash=API_HASH,
                                                  phone_number=self.credentials['phone'],
                                                  workdir=self.fdir,
                                                  test_mode=test_mode)
        if INIT_SESSION:
            app._link = self.credentials['link']
        logging.info(f"signing in {self.credentials['phone']}")
        #app.start()
        app.add_handler(pyrogram.MessageHandler(self.handle_message))
        self.app = app

        threading.Thread(target=self.app.run).start()
        threading.Thread(target=self.watcher).start()

    def __init__(self, channel):
        self.channel = channel
        self.credentials = channel['credentials']
        self.fdir = f'../{gen_random_string()}'
        os.mkdir(self.fdir)
        threading.Thread(target=self.full_init).start()

    def watcher(self, delay=3):
        while time.sleep(delay) is None:
            if not processer.check_if_alive_and_update(self.channel['_id']):
                self.app.stop()
                processer.remove_channel(self.channel['_id'])
                break


    def handle_file(self, update):
        pass

    def handle_message(self, client, update):
        chat_id = update.chat.id
        from_ = update.from_user
        author = update.username if from_.username is not None else f'TgUser{update.id}'
        if from_.first_name is not None:
            author_name = from_.first_name
            if from_.last_name is not None:
                author_name = author_name + ' ' + from_.last_name
        else:
            author_name = author

        print(f"update: {update}")
        if str(from_.id) == self.credentials['self_id']:
            logging.debug('our message')
            return
        if update['message']['content']['@type'] == "messageDocument":
            pass
        else:
            message_text = message.text

            message = {
                'mtype': 'message',
                'text': message_text,
                'author': str(author),
                'author_name': author_name,
                'author_type': 'user',
                'thread_id': str(chat_id),
                'channel': CHANNEL,
                'timestamp': update.date*1000,
                'server_timestamp': get_server_timestamp(),
            }

            print(message)
            add_new_message(message)

    def __del__(self):
        # maybe, it should update db in credentials
        time.sleep(5)
        print('deleted..')
        logging.info('updating db state in mongo')
        fpath = f'/tmp/{gen_random_string()}.tar'
        shutil.make_archive(fpath, 'tar', self.fdir)
        content = get_b64_file(fpath)
        os.remove(fpath)
        channels.update_one({'_id': self.channel['_id']}, {'credentials.db': content})
        shutil.rmtree(self.fdir)

processer = ServerStyleProcesser(CHANNEL, TgListener)
processer.listen_to_new_channels()
