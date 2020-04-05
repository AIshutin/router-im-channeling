import time
import requests
import threading
import time
from itertools import chain
import imaplib
import datetime
from enum import Enum
import json
from werkzeug.exceptions import HTTPException
import base64
import pymongo
import hashlib
import hmac
import six
import random
import os
from urllib.parse import urlparse
import logging
from common import *

CHANNEL = 'fb'
SECRET_FB_KEY = "StFL2meTu5go8tcrHF7J"
def validate_hub_signature(request_payload, hub_signature_header, app_secret=SECRET_FB_KEY):
    return True

"""
JSON {'object': 'page', 'entry': [{'id': '101962504709802', 'time': 1580667231655, 'messaging': [{'sender': {'id': '2673203139464950'}, 'recipient': {'id': '101962504709802'}, 'timestamp': 1580667231259, 'message': {'mid': 'm_SER-4imvTXXOIgCEK2xJ4SFcNRQ5kMmh8qxWJuWPyLw_770YPPIxeZkQ-xtNDsREzhijuFsRXYeIVu8pEInIhw', 'text': 'erfgrfzdsgrehgerh'}}]}]}
"""

def run(request):
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token != SECRET_FB_KEY:
            return ""
        if mode == 'subscribe':
            logging.info('WEBHOOK_VERIFIED', challenge)
            return challenge
        else:
            return ''
    elif request.method == 'POST':
        json_data = request.get_json(force=True)
        logging.debug(json_data)
        object = json_data['object']
        entry = json_data['entry']
        sha1 = request.headers.get('X-Hub-Signature')
        raw_data = request.get_data()
        assert(validate_hub_signature(raw_data, sha1))

        for event in entry:
            for messaging in event['messaging']:
                #print(messaging, type(messaging))
                sender_id = messaging['sender']['id']
                recipient_id = messaging['recipient']['id']
                time = messaging['timestamp']
                text = messaging['message'].get('text', '')
                logging.info('recipient_id', recipient_id)
                logging.info('sender_id', sender_id)
                logging.info('text', text)
                result = channels.find_one({'webhook_token': recipient_id})
                if result is None:
                    logging.info(f"No workspace exist for recipient_id {recipient_id}")
                    continue

                msg = {
                    'mtype': 'text',
                    'text': text,
                    'author': f'FB_{sender_id}',
                    'author_name': f'FB_{sender_id}',
                    'author_type': 'user',
                    'thread_id': sender_id,
                    'channel': CHANNEL,
                    'channel_id': str(result['_id']),
                    'timestamp': time, # miliseconds
                    'server_timestamp': get_server_timestamp(),
                    'original_ids': [messaging['message']['mid']],
                }

                if 'reply_to' in messaging['message']:
                    mid = messaging['message']['reply_to']['mid']
                    reply_id = -1
                    for el in messages.find({'original_id': mid, 'thread_id': sender_id})\
                                                             .sort([('service_timestamp', 1)]):
                        reply_id = str(el['_id'])
                        break
                    logging.debug(reply_id)
                    msg['reply_id'] = reply_id

                was = False
                logging.debug(messaging)
                attachments = []
                for attachment in messaging['message'].get('attachments', {}):
                        if attachment['type'] == 'location':
                            continue
                        mtype = 'file'
                        if attachment['type']== 'image':
                            mtype = 'image'
                        logging.debug('Attachment', attachment)
                        link = attachment['payload']['url']
                        if link is None or len(link) == 0:
                            continue

                        r = requests.get(link)
                        fpath = f'/tmp/{gen_random_string(30)}'
                        with open(fpath, 'wb') as f:
                            f.write(r.content)

                        content = get_b64_file(fpath)
                        os.remove(fpath)

                        file = {'type': mtype,
                                'content': content,
                                'name': urlparse(link).path.split('/')[-1]}
                        if attachments is None:
                            attachments = [file]
                        else:
                            attachments.append(file)
                if attachments is not None and len(attachments) != 0:
                    msg['attachments'] = attachments

                Message(**msg)
                add_new_message(msg)

        return 'Hello, World'
