from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import random
import threading
import mimetypes

SECRET_INTERNAL_KEY = 'DaGKO1awbMaZ1WgeaLUQ'
BASE_URL = 'https://cerebra-test.herokuapp.com/'

alphabet=list('0123456789')
for i in range(26):
    alphabet.append(chr(ord('a') + i))
    alphabet.append(chr(ord('A') + i))

def gen_random_string(length=30):
    return ''.join([alphabet[random.randint(0, len(alphabet) - 1)] for i in range(length)])

def get_mime_type(fpath):
    ctype, encoding = mimetypes.guess_type(fpath)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    return (maintype, subtype)


class Channels(str, Enum):
    tg = 'tg'
    vk = 'vk'
    email = 'email'
    fb = 'fb'

class ChannelCredentials(BaseModel):
    token: str = ""
    link: str = ""
    login: str = ""
    password: str = ""
    name: Channels
    smpt: str = ""
    imap: str = ""
    self_id: str = ""
    phone: str = ""

class MessageType(str, Enum):
    text = 'text'
    file = 'file'
    image = 'image'

class AccessType(str, Enum):
    admin = "admin"
    agent = "agent"

class AuthorType(str, Enum):
    agent = 'agent'
    user = 'user'

class Message(BaseModel):
    mtype: MessageType
    content: Optional[str] = ''
    text: Optional[str] = ''
    author: str
    author_name: str
    author_type: AuthorType
    thread_id: str = ""
    channel: Channels
    timestamp: int
    file_format: str = Field('jpg')
    message_id: int = Field(-1, description="When sending messages to server should be omitted/set to -1")
    original_id: str = Field(None)
    email_subject: str = Field(None)

'''
def delayed_func(func, delay, ):
    threading.Thread(target: .start()
    time.sleep(delay)
'''
