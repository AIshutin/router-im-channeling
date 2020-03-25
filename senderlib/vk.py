from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    save_b64_to_file, AttachmentType, fallback_attachment_caption
import threading
import requests
import os
import time
import shutil
import requests
import base64
import pydantic
from typing import Optional, List
import vk_api
import logging
import random

CHANNEL = Channels.vk

SECRET_VK_KEY = os.getenv('SECRET_VK_KEY', '9YAVEQAraTr4pClNDjvg')
VK_RQ_DELAY = int(os.getenv('VK_RQ_DELAY', 6))

logging.info(f'{SECRET_VK_KEY} used as SECRET_VK_KEY')
logging.info(f'{VK_RQ_DELAY} used as VK_RQ_DELAY')

class VkCredentials(pydantic.BaseModel):
    token: str
    self_id: str

def send_message(message: Message, credentials: VkCredentials, replied: Optional[Message]=None) -> str:
    reply_to = replied
    vk = vk_api.VkApi(token=credentials.token).get_api()
    reply = None
    if replied is not None:
        logging.debug(reply_to, message)
        reply = int(replied.original_ids[0])
    forward_messages = None
    #print(forwarded, type(forwarded))
    if message.forwarded is not None and len(message.forwarded) != 0:
        forward_messages = []
        for el in message.forwarded:
            forward_messages += el.original_ids
    text = message.text
    vk_attachment_ids = []
    if message.attachments is not None and len(message.attachments) != 0:
        for attachment in message.attachments:
            file_content = attachment.content
            caption = attachment.caption
            my_id = int(credentials.self_id)
            logging.debug(my_id)
            fdir = f'/tmp/{gen_random_string(30)}/'
            os.mkdir(fdir)
            fpath = f'{fdir}{attachment.name}'
            save_b64_to_file(file_content, fpath)
            if attachment.type == AttachmentType.image:
                res = vk.photos.getMessagesUploadServer(peer_id=message.thread_id)
                res2 = requests.post(res['upload_url'], files={"file1": (fpath, open(fpath, 'rb'))})
                logging.debug(res2.text)
                js = res2.json()
                res3 = vk.photos.saveMessagesPhoto(server=js['server'], photo=js['photo'],
                                            hash=js['hash'], caption=caption)
                logging.debug(res3)
                photo_id = res3[0]['id']
                owner_id = res3[0]['owner_id']
                logging.debug(photo_id)

                atype = 'photo'
                name = f"{atype}{owner_id}_{photo_id}"
            else:
                upl = vk_api.VkUpload(vk)
                res = upl.document_wall(fpath, group_id=my_id)
                logging.debug(res)
                id = res['doc']['id']
                tp = res['type']
                owner_id = res['doc']['owner_id']
                name = f"{tp}{owner_id}_{id}"
            text = fallback_attachment_caption(attachment, only_format=True) + text
            vk_attachment_ids.append(name)
            shutil.rmtree(fdir)
    else:
        vk_attachment_ids = None

    logging.debug(f"ForwardedOriginalIds: {forward_messages}")
    resp = vk.messages.send(user_id=int(message.thread_id),
                            message=text,
                            random_id=random.randint(1, int(1e17)),
                            reply_to=reply,
                            attachment=vk_attachment_ids,
                            forward_messages=forward_messages)
    return [str(resp)]

SERVER_TITLE = 'router-im'

def data_flow_hack(credentials: VkCredentials, tail, delay=VK_RQ_DELAY):
    """
    We need to add tail information to db before Vk confirmation request.
    Thus, we'll add server to vk after {delay}.
    """
    time.sleep(delay)
    vk = vk_api.VkApi(token=credentials.token).get_api()
    resp = vk.groups.addCallbackServer(group_id=int(credentials.self_id),
                                        url=f'{BASE_URL}{CHANNEL}/{tail}',
                                        title=SERVER_TITLE,
                                        secret_key=SECRET_VK_KEY)
    logging.debug(resp)
    server_id = resp['server_id']
    logging.info(f'SERVER_ID {server_id}')
    #resp = vk.groups.getCallbackSettings(group_id=int(credentials.self_id),
    #                                     server_id=server_id)
    #resp['message_new'] = 1
    vk.groups.setCallbackSettings(group_id=int(credentials.self_id),
                                 server_id=server_id,
                                  message_new=1,
                                  message_edit=1,
                                  api_version='5.103')
    logging.debug('SERVER configured')

def add_channel(credentials: VkCredentials):
    tail = gen_random_string()
    threading.Thread(target=data_flow_hack, args=(credentials, tail, 3)).start()
    return tail

def remove_channel(credentials: VkCredentials):
    vk = vk_api.VkApi(token=credentials.token).get_api()
    cnt = 3
    while cnt > 0:
        result = vk.groups.getCallbackServers(group_id=int(credentials.self_id))
        server_id = None
        for el in result['items']:
            if el['title'] == SERVER_TITLE:
                server_id = el['id']
        if server_id is None:
            cnt -= 1
            time.sleep(VK_RQ_DELAY)
            continue
        vk.groups.deleteCallbackServer(group_id=int(credentials.self_id),
                                       server_id=server_id)
        return
    logging.warning(f'vk server {SERVER_TITLE} was not found')
