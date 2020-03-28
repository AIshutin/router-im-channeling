from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    save_b64_to_file, fallback_reply_to, fallback_forward, \
                    AttachmentType
import threading
import requests
import os
import time
import shutil
import requests
import base64
import pydantic
from typing import Optional, List
import json
import logging

class FbCredentials(pydantic.BaseModel):
    token: str
    self_id: str

def send_message(message: Message, credentials: FbCredentials, replied=Optional[Message]):
    token = credentials.token
    link = f'https://graph.facebook.com/v5.0/me/messages?access_token={token}'
    text = message.text

    if message.forwarded is not None:
        for el in message.forwarded:
            text = fallback_forward(el) + text

    if replied is not None:
        text = fallback_reply_to(replied) + text

    original_ids = []

    if message.text is not None and len(message.text) != 0:
        json_data = {"messaging_type": "UPDATE",
                    "recipient":{
                      "id": message.thread_id
                    },
                    "message":{
                      "text": text
                    }
                  }
        resp = requests.post(link, json=json_data)
        logging.debug(resp.text)
        resp.raise_for_status()
        # return

    if message.attachments is not None:
        for attachment in message.attachments:
            type = "file"
            if attachment.type == AttachmentType.image:
                type = AttachmentType.image

            fdir = f'/tmp/{gen_random_string(30)}/'
            os.mkdir(fdir)
            fpath = fdir + attachment.name
            save_b64_to_file(attachment.content, fpath)
            maintype, subtype = get_mime_type(fpath)


            message_str = 'message={"attachment":{"type":"' + type + '","payload":{"is_reusable":true}}}'
            filedata_str = f'filedata=@{fpath};type={maintype}/{subtype}'
            link = f'https://graph.facebook.com/v6.0/me/message_attachments?access_token={credentials.token}'
            command = f'curl \'{link}\' -F \'{message_str}\' -F \'{filedata_str}\' > {fdir}out.txt'
            code = os.system(command)
            if code != 0:
                logging.warning(f'Attachment {attachment} was not sent to FB')
                continue
            attachment_id = json.load(open(fdir + 'out.txt', 'r'))['attachment_id']
            shutil.rmtree(fdir)
            logging.debug(attachment_id)


            link = f'https://graph.facebook.com/v6.0/me/messages?access_token={credentials.token}'
            data = {"recipient": {
                        "id": message.thread_id
                        },
                    "message":{
                        "attachment":{
                        "type": type,
                        "payload":{
                            "attachment_id": attachment_id
                            }
                        }
                    },
                    "messaging_type": "UPDATE",
                }
            response = requests.post(link, json=data)
            print(response.text)
            response.raise_for_status()
            # response.json()['message_id']
    return original_ids

FB_TAIL = ""

def add_channel(credentials: FbCredentials):
    tail = credentials.self_id
    return tail

def remove_channel(credentials: FbCredentials):
    pass
