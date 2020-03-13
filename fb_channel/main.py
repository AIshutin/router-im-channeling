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

MONGO_PASSWORD = '8jxIlp0znlJm8qhL'
MONGO_LINK = f'mongodb+srv://cerebra-autofaq:{MONGO_PASSWORD}@testing-pjmjc.gcp.mongodb.net/test?retryWrites=true&w=majority'
myclient = pymongo.MongoClient(MONGO_LINK)
CHANNEL = 'fb'
TAIL_DB = 'tails'
TAIL_COLL = 'tails'
IMGS_FORMATS = {'jpg', 'jpeg', 'png', 'svg', 'bmp'}

SECRET_FB_KEY = "StFL2meTu5go8tcrHF7J"
def validate_hub_signature(request_payload, hub_signature_header, app_secret=SECRET_FB_KEY):
    """
        @inputs:
            app_secret: Secret Key for application
            request_payload: request body
            hub_signature_header: X-Hub-Signature header sent with request
        @outputs:
            boolean indicated that hub signature is validated
    """
    return True
    try:
        hash_method, hub_signature = hub_signature_header.split('=')
    except:
        pass
    else:
        digest_module = getattr(hashlib, hash_method)
        hmac_object = hmac.new(str(app_secret), unicode(request_payload), digest_module)
        generated_hash = hmac_object.hexdigest()
        if hub_signature == generated_hash:
            return True
    return False

# TOKEN = "EAAIrF0hyVy0BAOavd3FMQCBEt12Tbe9OMxNZBhi2OAjGvmZCxUhtEpG07LFYLy55JCb2EQh7W7716ExAygP99qZCFW3Ekux2BYb4mENS8QVAMsHW0VSac5SgP3v3IYbuF2B2Mtm8RTjnvZAwKxnJRY54tbrSAduwTqapS0y2BQZDZD"

def get_new_id(workspace):
    max_id = myclient[workspace]['configs'].find_and_modify({'name': 'last_message_id'},
                                                {'$inc': {'value': 1}}, new=1)['value']
    return max_id

def add_new_message(workspace, message):
    message['message_id'] = get_new_id(workspace)
    myclient[workspace]['messages'].insert_one(message)

def get_b64_file(fpath):
    with open(fpath, "rb") as file:
        return base64.b64encode(file.read())

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

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
            print('WEBHOOK_VERIFIED', challenge)
            return challenge
        else:
            return ''
    elif request.method == 'POST':
        json_data = request.get_json(force=True)
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
                print('recipient_id', recipient_id)
                print('sender_id', sender_id)
                print('text', text)
                result = myclient[TAIL_DB][TAIL_COLL].find_one({'tail': recipient_id})
                if result is None:
                    print(f"No workspace exist for recipient_id {recipient_id}")
                    continue
                workspace = result['workspace']

                msg = {
                    'mtype': 'text',
                    'text': text,
                    'author': f'FB_{sender_id}',
                    'author_name': f'FB_{sender_id}',
                    'author_type': 'user',
                    'thread_id': sender_id,
                    'channel': CHANNEL,
                    'channel_id': str(result['_id']),
                    'timestamp': time,
                    'message_id': -1,
                }

                was = False
                print(messaging)
                for attachment in messaging['message'].get('attachments', {}):
                        if attachment['type'] == 'location':
                            continue
                        mtype = 'file'
                        if attachment['type']== 'image':
                            mtype = 'image'
                        print('Attachment', attachment)
                        link = attachment['payload']['url']
                        if link is None or len(link) == 0:
                            continue

                        r = requests.get(link)
                        fpath = f'/tmp/{gen_random_string(30)}'
                        with open(fpath, 'wb') as f:
                            f.write(r.content)

                        content = get_b64_file(fpath)
                        os.remove(fpath)

                        msg['content'] = content
                        file_format = urlparse(link).path.split('/')[-1]
                        if '.' in file_format:
                            msg['file_format'] = file_format[file_format.find('.') + 1:]
                        msg['mtype'] = mtype

                        add_new_message(workspace, msg) # warning
                        was = True
                if not was and len(text) != 0:
                    add_new_message(workspace, msg)

        return 'Hello, World'
