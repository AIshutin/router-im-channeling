from typing import Optional
from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    save_b64_to_file, AttachmentType
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

CHANNEL = Channels.vk
SECRET_VK_KEY = '9YAVEQAraTr4pClNDjvg'

class VkCredentials(pydantic.BaseModel):
    token: str
    self_id: str
    code: str

def send_message(message: Message, credentials: VkCredentials, replied: Optional[Message]=None,
                                                               forwarded: Optional[List[Message]]=None) -> str:
    reply_to = replied
    vk = vk_api.VkApi(token=credentials.token).get_api()
    reply = None
    if reply_to is not None and message.reply_to != -1:
        print(reply_to, message)

        reply = int(reply_to.original_id)
    forward_messages = None
    #print(forwarded, type(forwarded))
    if forwarded is not None and len(forwarded) != 0:
        forward_messages = []
        for el in forwarded:
            forward_messages.append(el.original_id)

    vk_attachment_ids = []
    if message.attachments is not None and len(message.attachments is not None):
        for attachment in message.attachments:
            file_content = message.content
            caption = message.text
            my_id = int(credentials.self_id)
            print(my_id)
            fpath = f'/tmp/{gen_random_string(30)}/{attachment.name}'
            save_b64_to_file(message.content, fpath)
            if attachment.type == AttachmentType.image:
                res = vk.photos.getMessagesUploadServer(peer_id=message.thread_id)
                res2 = requests.post(res['upload_url'], files={"file1": (fpath, open(fpath, 'rb'))})
                print(res2.text)
                js = res2.json()
                res3 = vk.photos.saveMessagesPhoto(server=js['server'], photo=js['photo'],
                                            hash=js['hash'])
                print(res3)
                photo_id = res3[0]['id']
                owner_id = res3[0]['owner_id']
                print(photo_id)

                atype = 'photo'
                name = f"{atype}{owner_id}_{photo_id}"
            else:
                upl = vk_api.VkUpload(vk)
                res = upl.document_wall(fpath, group_id=my_id)
                print(res)
                id = res['doc']['id']
                tp = res['type']
                owner_id = res['doc']['owner_id']
                name = f"{tp}{owner_id}_{id}"
            vk_attachment_ids.append(name)
            shutil.rmtree(fpath)
    else:
        vk_attachment_ids = None

    resp = vk.messages.send(user_id=int(message.thread_id),
                            message=message.text,
                            random_id=message.message_id,
                            reply_to=reply,
                            attachment=vk_attachment_ids)
    return resp

SERVER_TITLE = 'router-im'

def data_flow_hack(credentials: VkCredentials, tail, delay=6):
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
    print(resp)
    server_id = resp['server_id']
    print(server_id)
    #resp = vk.groups.getCallbackSettings(group_id=int(credentials.self_id),
    #                                     server_id=server_id)
    #resp['message_new'] = 1
    vk.groups.setCallbackSettings(group_id=int(credentials.self_id),
                                 server_id=server_id,
                                  message_new=1,
                                  message_edit=1,
                                  api_version='5.103')

def add_channel(credentials: VkCredentials):
    tail = gen_random_string()
    threading.Thread(target=data_flow_hack, args=(credentials, tail, 3)).start()
    return tail

def remove_channel(credentials: VkCredentials):
    vk = vk_api.VkApi(token=credentials.token).get_api()
    result = vk.groups.getCallbackServers(group_id=int(credentials.self_id))
    server_id = None
    for el in result['items']:
        if el['title'] == SERVER_TITLE:
            server_id = el['id']
    vk.groups.deleteCallbackServer(group_id=int(credentials.self_id),
                                   server_id=server_id)
