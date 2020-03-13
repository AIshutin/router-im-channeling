from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    save_b64_to_file
import threading
import requests
import os
import time
import shutil
import requests
import base64
import pydantic

class FbCredentials(pydantic.BaseModel):
    token: str
    self_id: str
    name: str = Channels.fb

def send_message(message: Message, credentials: FbCredentials):
    token = credentials.token
    link = f'https://graph.facebook.com/v5.0/me/messages?access_token={token}'
    if message.mtype == MessageType.text:
        resp = requests.post(link,
            json={"messaging_type": 'RESPONSE',#"UPDATE",
                  "recipient": {
                        "id": message.thread_id
                  },
                  "message": {
                        "text": message.text
                  }})
        print(resp.text)
        resp.raise_for_status()
        return
    mtype = 'image' if message.mtype == MessageType.image else 'file'

    """
    "message":{
            "attachment":{
              "type": mtype,
              "payload":{
                "url":"http://www.messenger-rocks.com/image.jpg",
                "is_reusable": True
              }
            }
          }
    """

    fpath = f'/tmp/{gen_random_string(30)}.{message.file_format}'
    save_b64_to_file(message.content, fpath)
    maintype, subtype = get_mime_type(fpath)

    '''files = {
        'recipient': {"id": message.thread_id},
        'message': {"attachment": {"type": mtype, "payload": {"is_reusable": False}}},
        'filedata': (open(fpath, 'rb'), f'type={maintype}/{subtype}'),
    }'''

    msg_string = '{"attachment":{"type":"{' + mtype + '}", "payload":{"is_reusable"=false}}}'
    rec_string = '{"id":"' + message.thread_id + '"}'
    headers = {'Content-type': 'multipart/form-data'}
    files = {
        'filedata': (fpath, open(fpath, 'rb'), f'{maintype}/{subtype}')
    }

    data = {
        'recipient': {"id": message.thread_id},
        'message': {"attachments": {"type": mtype, "payload": {"is_reusable": False}}}
    }

    rq = requests.Request(url=link, files=files, headers=headers, data=data).prepare()
    print(rq.body)

    print(files)
    response = requests.post(link, files=files, json=data)
    print(response.text)
    response.raise_for_status()
    os.remove(fpath)

FB_TAIL = ""

def add_channel(credentials: FbCredentials):
    tail = credentials.self_id
    return tail

def remove_channel(credentials: FbCredentials):
    pass
