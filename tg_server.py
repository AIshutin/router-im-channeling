import pyrogram
from common import *
import os
import sys
import io
import logging
import requests
import time
import threading
import shutil
import pyrohacks
from bson.objectid import ObjectId
from senderlib.common import fallback_reply_to, fallback_forward
from fastapi import FastAPI, Query, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import copy

logging.basicConfig(level=logging.DEBUG)
pyrogram.Client.authorize = pyrohacks.custom_authorize
pyrogram.Client.idle = pyrohacks.idle

CHANNEL = 'tg'
API_ID = os.getenv('API_ID', "1087174")
API_HASH = os.getenv('API_HASH', "3370ae6b2b06dad548626a0fdafc14dc")
logging.info(f'{API_ID} used as API_ID for Telegram')
logging.info(f'{API_HASH} used as API_HASH for Telegram')
TITLE = "Router.im server"
SESSION_FILE_NAME = f'{TITLE}.session'
BASE_URL = os.getenv('OUR_URL', 'http://localhost:8000')
if BASE_URL[-1] != '/':
    BASE_URL = BASE_URL + '/'
TOKEN = gen_random_string()
FINAL_URL = BASE_URL + TOKEN

class TgListener:
    url = FINAL_URL

    def extract_userdate(self, user):
        if user is None:
            return "", ""
        author = getattr(user, 'username', f'TgUser{user.id}')
        author_name = ''
        if getattr(user, 'first_name', None) != '':
            author_name = user.first_name
        if getattr(user, 'last_name', None) != '':
            if author_name != '':
                author_name = author_name + ' '
            author_name = author_name + user.last_name
        if author_name == '':
            author_name = author
        return (author, author_name)

    def send_message(self, message):
        original_ids = []
        reply_to = None
        text = message.get('text', '')
        chat_id = message['thread_id']
        if chat_id != 'me':
            chat_id = int(chat_id)
        if text is None:
            text = ''
        if message.get('reply_to', None) is not None:
            reply_to = ObjectId(message['reply_to'])
            res = messages.find_one({'_id': reply_to})
            if res is not None and res.get('original_ids', []) is not None and \
                                    res.get('original_ids', []) != []:
                reply_to = int(res['original_ids'][0])
            else:
                text = fallback_reply_to(reply_to) + text
                reply_to = None
        if text != '':
            id = self.app.send_message(chat_id=chat_id,
                                       text=text,
                                       reply_to_message_id=reply_to).message_id
            reply_to = None
            original_ids.append(str(id))

        if message.get('attachments', None) is not None:
            for attachment in message['attachments']:
                fdir = f'/tmp/{gen_random_string()}/'
                os.mkdir(fdir)
                fpath = fdir + attachment['name']
                save_b64_to_file(attachment['content'], fpath)
                if attachment['type'] == 'photo':
                    id = self.app.send_photo(chat_id=chat_id,
                                            photo=fpath,
                                            reply_to_message_id=reply_to,
                                            caption=attachment.get('caption', None)).message_id
                else:
                    id = self.app.send_document(chat_id=chat_id,
                                                document=fpath,
                                                reply_to_message_id=reply_to,
                                                caption=attachment.get('caption', None)).message_id
                reply_to = None
                original_ids.append(str(id))
                shutil.rmtree(fdir)
        if reply_to is not None:
            id = self.app.send_message(chat_id=chat_id,
                                       text='>',
                                       reply_to_message_id=reply_to).message_id
            reply_to = None
            original_ids.append(id)

        if message.get('forwarded', None) is not None:
            for forwarded in message['forwarded']:
                if forwarded.get('original_ids', None) is not None and \
                    forwarded['original_ids'] != []:
                    self.app.forward_messages(chat_id=chat_id,
                                                from_chat_id=chat_id,
                                                message_ids=map(int, forwarded['original_ids']))
                else:
                    for el in forwarded:
                        text = fallback_forward(el)
                        self.app.send_document(chat_id=chat_id,
                                                text=text)
        return original_ids

    def full_init(self):
        # reserve this channel for us
        result = processer.check_if_alive_and_update(self.channel['_id'], self)
        if not result:
            processer.remove_channel(self.channel['_id'])
            return

        INIT_SESSION = False
        if self.credentials.get('db', None) is None:
            INIT_SESSION = True
            logging.debug('initializing new session..')
            test_mode = False
            if self.credentials['link'] == 'http://localhost:2000/_tg_get_code/2':
                test_mode = True
            logging.debug(f"Test mode: {test_mode}")
            app = pyrogram.Client(TITLE, api_id=API_ID,
                                          api_hash=API_HASH,
                                          phone_number=self.credentials['phone'],
                                          workdir=self.fdir,
                                          test_mode=test_mode)
            app._link = self.credentials['link']
            logging.info(f"signing in {self.credentials['phone']}")
            app.start()

            app.stop()
            logging.info('updating db state in mongo')
            content = get_b64_file(f'{self.fdir}/{SESSION_FILE_NAME}')
            channels.update_one({'_id': self.channel['_id']},
                {'$set': {'credentials.db': content, 'link': None}})
        else:
            save_b64_to_file(self.credentials['db'], f"{self.fdir}/{SESSION_FILE_NAME}")

        app = pyrogram.Client(TITLE, workdir=self.fdir,
                                    api_id=API_ID,
                                    api_hash=API_HASH,)
        app.add_handler(pyrogram.MessageHandler(self.handle_message))
        logging.debug('INIT done')
        self.app = app
        threading.Thread(target=self.app.run).start()
        threading.Thread(target=self.watcher).start()

    def __init__(self, channel, def_time):
        self.channel = channel
        self.credentials = channel['credentials']
        self.fdir = f'../{gen_random_string()}'
        self.def_time = def_time
        os.mkdir(self.fdir)
        threading.Thread(target=self.full_init).start()

    def watcher(self, delay=3):
        while time.sleep(delay) is None:
            if not processer.check_if_alive_and_update(self.channel['_id'], self):
                try:
                    self.app.stop()
                except ConnectionError: # already stopped
                    pass
                processer.remove_channel(self.channel['_id'])
                break

    def handle_file(self, update):
        pass

    def handle_message(self, client, update):
        chat_id = update.chat.id
        author, author_name = self.extract_userdate(update.from_user)

        logging.debug(f"update: {update}")
        if update.outgoing:
            logging.debug('our message')
            return

        message_text = update.text

        message = {
            'mtype': 'message',
            'text': message_text,
            'author': str(author),
            'author_name': author_name,
            'author_type': 'user',
            'thread_id': str(chat_id),
            'channel': CHANNEL,
            'channel_id': str(self.channel['_id']),
            'timestamp': int(update.date*1000),
            'server_timestamp': get_server_timestamp(),
        }

        if getattr(update, 'media', False):
            try:
                path = update.download()
                type_ = 'image' if hasattr(update, 'photo') and update.photo is not None \
                                else 'file'
                name = os.path.basename(path)
                attachments = [{'type': type_, 'content': get_b64_file(path), \
                                'name': name, 'caption': update.caption}]
                message['attachments'] = attachments
            except ValueError:
                logging.debug('no attachments despite message.media is True')

        if getattr(update, 'reply_to_message', None) is not None:
            reply_to = None
            original_id = str(update.reply_to_message.message_id)
            res = messages.find_one({'channel': CHANNEL,
                                    'channel_id': self.channel['_id'],
                                    'thread_id': str(chat_id),
                                    'original_ids': original_id})
            if res is not None:
                reply_to = str(res['_id'])
                message['reply_to'] = str(res['_id'])

        if getattr(update, 'forward_date', None) is not None:
            forwarded = message
            message = {
                'mtype': 'message',
                'text': message_text,
                'author': str(author),
                'author_name': author_name,
                'author_type': 'user',
                'thread_id': str(chat_id),
                'channel': CHANNEL,
                'channel_id': str(self.channel['_id']),
                'timestamp': int(update.date*1000),
                'server_timestamp': get_server_timestamp(),
            }

            if getattr(update, 'forward_sender_name', None) is not None:
                forwarded['author'] = forwarded['author_name'] = update.forward_sender_name
            else:
                forwarded['author'], forwarded['author_name'] = self.extract_userdate(update.forward_from)

            if getattr(update, 'forward_from_message_id', None) is not None:
                original_id = update.forward_from_message_id
                res = messages.find_one({'channel': CHANNEL,
                                        'channel_id': self.channel['_id'],
                                        'thread_id': str(chat_id),
                                        'original_ids': original_id})
                if res is not None:
                    forwarded['original_ids'] = [str(res['_id'])]
            forwarded.pop('reply_to', None)
            forwarded.pop('thread_id', None)
            forwarded.pop('channel_id', None)
            message['forwarded'] = [forwarded]

        message['original_ids'] = [str(update.message_id)]

        if getattr(update, 'edit_date', None) is not None:
            query = {'channel': CHANNEL,
                    'channel_id': self.channel['_id'],
                    'thread_id': str(chat_id),
                    'original_ids': str(update.message_id),
                    'mtype': 'message'}
            original = messages.find_one(query)
            if original is None:
                logging.warning(f'Unedited message for {update.message_id} in {str(chat_id)} not found')
            else:
                message['unedited'] = str(original['_id'])
                message['mtype'] = 'edit'
                query.pop('mtype')
                message['mversion'] = messages.count(query)
        logging.debug(message)
        Message(**message)
        add_new_message(message)

processer = ServerStyleProcesser(CHANNEL, TgListener)
threading.Thread(target=processer.listen_to_new_channels).start()

app = FastAPI()

@app.post(f'/{TOKEN}')
def send_message(message: dict = Body(..., embed=True)):
    result = processer.channels2listeners[message['channel_id']].send_message(message)
    return {'original_ids': result}
