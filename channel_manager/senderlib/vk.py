from typing import Optional
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
import vk_api

CHANNEL = Channels.vk
SECRET_VK_KEY = '9YAVEQAraTr4pClNDjvg'

class VkCredentials(pydantic.BaseModel):
    token: str
    self_id: str
    code: str
    name: str = Channels.vk
    assert(name == Channels.vk)

def send_message(message: Message, credentials: VkCredentials):
    vk = vk_api.VkApi(token=credentials.token).get_api()

    if message.mtype == MessageType.text:
        vk.messages.send(user_id=int(message.thread_id),
                message=message.text,
                random_id=message.message_id)
    elif message.mtype == MessageType.image or message.mtype == MessageType.file:
        file_content = message.content
        caption = message.text
        my_id = credentials.self_id
        print(my_id)

        fpath = f'/tmp/{gen_random_string(30)}.{message.file_format}'
        save_b64_to_file(message.content, fpath)

        if message.mtype == MessageType.image:
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

            print(name)
            resp = vk.messages.send(user_id=int(message.thread_id),
                    attachment=name,
                    message=caption,
                    random_id=message.message_id)
            print(resp)
            '''
            [{'id': 457239302, 'album_id': -64, 'owner_id': 421581863, 'sizes': [{'type': 's', 'url': 'https://sun9-33.userapi.com/c858528/v858528688/f33e0/glAAFxKU5TM.jpg', 'width': 75, 'height': 54}, {'type': 'm', 'url': 'https://sun9-54.userapi.com/c858528/v858528688/f33e1/-RrwCybVrMA.jpg', 'width': 112, 'height': 81}, {'type': 'x', 'url': 'https://sun9-56.userapi.com/c858528/v858528688/f33e2/OFaWItVqxlY.jpg', 'width': 112, 'height': 81}, {'type': 'o', 'url': 'https://sun9-55.userapi.com/c858528/v858528688/f33e3/UxiXm-6Tw5M.jpg', 'width': 112, 'height': 81}, {'type': 'p', 'url': 'https://sun9-70.userapi.com/c858528/v858528688/f33e4/tjoBVx3XW4E.jpg', 'width': 112, 'height': 81}, {'type': 'q', 'url': 'https://sun9-54.userapi.com/c858528/v858528688/f33e5/0JT_6QJx_o4.jpg', 'width': 112, 'height': 81}, {'type': 'r', 'url': 'https://sun9-49.userapi.com/c858528/v858528688/f33e6/aAPtF6CJdMY.jpg', 'width': 112, 'height': 81}], 'text': '', 'date': 1582716225, 'access_key': 'a542b74c2d19db1516'}]
            '''
        else:
            res = vk.docs.getWallUploadServer(group_id=my_id) # doesn't work
            upload_url = res['upload_url']
            res2 = requests.post(upload_url, files={"file1": (fpath, open(fpath, 'rb'))})
            print(res2.text)
            js = res2.json()
            res3 = vk.docs.save(file=js['file'])
            print(res3)

            doc = res3[0]
            id = doc['id']
            owner_id = doc['id']
            if 'type' in doc:
                tp = doc['type']
            else:
                tp = 'doc'
            name = f"{tp}{owner_id}_{id}"

            print(name)
            resp = vk.messages.send(user_id=int(message.thread_id),
                            attachment=name,
                            message=text,
                            random_id=message.message_id)
            print(resp)
        os.remove(fpath)

    print('SENT')

SERVER_TITLE = 'router-im'

def data_flow_hack(credentials: VkCredentials, tail, delay=3):
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
