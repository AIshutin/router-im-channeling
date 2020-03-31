import pymongo
from common import *
from datetime import datetime
import os
import shutil
import threading
import random
import asyncio
from aioimaplib import aioimaplib
import time
import mailparser
from bs4 import BeautifulSoup
import logging

LOG_LEVEL = logging.DEBUG
logging.basicConfig(level=LOG_LEVEL)
# logging.disable(level=LOG_LEVEL)

CHANNEL = 'email'
MAX_CHANNELS_PER_INSTANCE = int(os.getenv('MAX_CHANNELS_PER_INSTANCE', 10))
channels2listeners = dict()
POLLING_TIME = int(os.getenv('POLLING_TIME', 60))
TIME_GAP = POLLING_TIME * 2
TIME_FIELD = 'webhook_token'
loop = asyncio.get_event_loop()

def clean_text_from_citation(text):
    text = '\n'.join(text)
    res = ""
    logging.debug(text)
    soup = BeautifulSoup(text, features="html5lib")
    res = soup.find('div')
    res = res.string
    if res is None:
        res = ''
    return res

@asyncio.coroutine
def process_new_message(host, user, password, uid, channel_id):
    logging.debug(f"uid: {uid}")
    imap_client = aioimaplib.IMAP4_SSL(host=host)
    yield from imap_client.wait_hello_from_server()

    yield from imap_client.login(user, password)
    yield from imap_client.select()
    result, data = yield from imap_client.fetch(uid, '(RFC822)')

    email_message = mailparser.parse_from_bytes(data[1])
    # email.message_from_bytes(data[1])
    msg = {'subject': email_message.subject,
           'from':    email_message.from_,
           'text':    clean_text_from_citation(email_message.text_html),
           'message_id': email_message.message_id}

    logging.info(msg['from'])
    name, email = msg['from'][0]
    logging.debug(f"name: {name} email: {email}")
    logging.debug(f"subject: {msg['subject']}")
    logging.debug(f"text: {msg['text']}")
    if msg['subject'] is None:
        msg['subject'] = ''
    text = msg['subject'] + '\n' + msg['text']

    message = {
        'mtype': 'message',
        'text': text,
        'author': email,
        'author_name': name,
        'author_type': 'user',
        'thread_id': email,
        'channel': CHANNEL,
        'timestamp': get_server_timestamp(),
        'server_timestamp': get_server_timestamp(), # not $CHANNEL timestamp!!
        'channel_id': str(channel_id)
    }

    message['original_ids'] = [msg['message_id']]

    logging.debug(email_message.reply_to)
    reply_to = None
    if email_message.reply_to != None and len(email_message.reply_to) != 0:
        reply_to = email_message.reply_to[0]
    logging.debug(f"in-reply-to: {email_message.in_reply_to}")
    if email_message.in_reply_to != None and len(email_message.in_reply_to) != 0:
        reply_to = email_message.in_reply_to
    if reply_to is not None:
        logging.debug(f"reply_to: {reply_to}")
        mid = messages.find_one({'channel': CHANNEL, 'original_ids': reply_to})
        if mid is not None:
            message['reply_to'] = str(mid['_id'])

    fdir = f'/tmp/{gen_random_string()}/'
    os.mkdir(fdir)
    email_message.write_attachments(fdir)
    attachments = []
    for el in os.listdir(fdir):
        logging.debug(el)
        name = str(el)
        caption = ""
        content = get_b64_file(fdir + el)
        type, subtype = get_mime_type(el)
        mtype = 'file'
        if type == 'image':
            mtype = type
        attachments.append({
            'type': mtype,
            'content': content,
            'name': name,
        })
    shutil.rmtree(fdir)

    if attachments != []:
        message['attachments'] = attachments

    logging.debug(f"message: {message}")
    add_new_message(message)

def check_if_alive_and_update(cid):
    if channels.find_one({'_id': cid}) is None:
        logging.debug(f'channel {cid} was deleted')
        return False
    current_time = str(int(get_server_timestamp() + TIME_GAP)//1000)
    res = channels.update_one({'_id': cid}, {'$max': {TIME_FIELD: current_time}})
    if res.modified_count == 0:
        logging.debug(f"probably, we are not responsible for processing channel {cid}")
        res2 = channels.find_one({'_id': cid})
        logging.debug(f"upd_value: {current_time}; original_value: {res2[TIME_FIELD]}")
        return False
    return True

@asyncio.coroutine
def wait_for_new_message(channel):
    credentials = channel['credentials']
    host, user, password = credentials['imap'], credentials['login'], credentials['password']

    imap_client = aioimaplib.IMAP4_SSL(host=host)
    yield from imap_client.wait_hello_from_server()
    yield from imap_client.login(user, password)
    yield from imap_client.select()

    while check_if_alive_and_update(channel['_id']):
        logging.debug('idle started')
        idle = yield from imap_client.idle_start(timeout=20)
        uid = -1
        while imap_client.has_pending_idle():
            logging.info('waiting...')
            msg = yield from imap_client.wait_server_push()
            logging.debug(f"!!!! msg: {msg}")
            flag = False
            if msg == aioimaplib.STOP_WAIT_SERVER_PUSH:
                res = imap_client.idle_done()
                _tmp = yield from asyncio.wait_for(idle, 3)
                if len(_tmp.lines) != 1:
                    logging.critical('Message may be missed')
                    logging.critical('Please, investigate logs to discover how to prevent this.')
                    logging.critical(_tmp.lines)
                flag = True
                msg = _tmp.lines
            for el in msg:
                if 'EXISTS' in el:
                    uid = el.split(' ')[0]
                    asyncio.ensure_future(process_new_message(host, user, password, uid, channel['_id']))
            if flag:
                break
    channels2listeners.pop(str(channel['_id']), None)
    yield from imap_client.logout()

    logging.info(f"email_listener_loop ended {channel}")

class EmailListener:
    def __init__(self, channel):
        logging.info(f"New channel: {channel}")
        loop.run_until_complete(wait_for_new_message(channel))

def add_new_channel(channel):
    channels2listeners[str(channel['_id'])] = EmailListener(channel)

def search_for_avaible_channels():
    current_time = str(int(get_server_timestamp()//1000))
    query = {TIME_FIELD: {'$lt': current_time},
            'channel_type': CHANNEL}
    for channel in channels.find(query):
        if len(channels2listeners) >= MAX_CHANNELS_PER_INSTANCE:
            break
        deadline = str(TIME_GAP + int(time.time()))
        add_new_channel(channel)

def listen_to_new_channels(period=3):
    while time.sleep(period) is None:
        search_for_avaible_channels()

listen_to_new_channels()
