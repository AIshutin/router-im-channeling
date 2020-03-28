from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Union
import random
import threading
import mimetypes
import base64
from bson.objectid import ObjectId
import bson
from datetime import datetime
import os
import logging

SECRET_INTERNAL_KEY = os.getenv('SECRET_INTERNAL_KEY', 'DaGKO1awbMaZ1WgeaLUQ')
BASE_URL = os.getenv('BASE_URL', 'https://cerebra-test.herokuapp.com/')

logging.info(f'{SECRET_INTERNAL_KEY} used as SECRET_INTERNAL_KEY')
logging.info(f'{BASE_URL} used as BASE_URL')

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

def save_b64_to_file(b64, fpath):
    with open(fpath, "wb") as file:
        return file.write(base64.b64decode(b64))

class Id(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, ObjectId) and not isinstance(v, str):
            raise TypeError('ObjectId required')
        res = v
        try:
            if isinstance(v, str):
                res = ObjectId(v)
        except bson.errors.InvalidId:
            logging.info(f'{v} is not ObjectId')
            raise TypeError(f'{v} is not ObjectId')
        return res

    @classmethod
    def __modify_schema__(cls, schema):
        schema.update({
            'Title': 'MongoDB ObjectID',
            'type': 'string'
        })

class AttachmentType(str, Enum):
    file = 'file'
    image = 'image'

class FileAttachment(BaseModel):
    type: AttachmentType = AttachmentType.file
    assert(type == AttachmentType.file)
    content: Optional[str]
    name: Optional[str]
    caption: Optional[str]

class ImageAttachment(FileAttachment):
    type: AttachmentType = AttachmentType.image
    assert(type == AttachmentType.image)

Attachment = Union[FileAttachment, ImageAttachment]

class Channels(str, Enum):
    tg = 'tg'
    tg_bot = 'tg_bot'
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
    message = 'message'
    edit = 'edit'

class AccessType(str, Enum):
    admin = "admin"
    agent = "agent"

class AuthorType(str, Enum):
    agent = 'agent'
    user = 'user'

class ForwardedMessage(BaseModel):
    mtype: MessageType = MessageType.message
    id: Optional[Id]
    attachments: Optional[List[Union[FileAttachment, ImageAttachment]]]
    text: Optional[str] = ''
    author: str
    author_name: str
    author_type: AuthorType
    channel: Optional[Channels]
    timestamp: Optional[int]
    server_timestamp: Optional[int]
    original_ids: Optional[List[str]] = None
    email_subject: Optional[str] = None

class Message(ForwardedMessage):
    """
    @ unedited - if mtype is MessageType.edit, Id of unedited message. Otherwise, \
    it's channel specific parameter which helps to find this message for linking \
    edited versions to it. Must be ommited when sending message to channel manager.
    """
    channel_id: Id
    thread_id: str = ""
    forwarded: Optional[List[ForwardedMessage]] = None
    reply_to: Optional[Id] = None
    mversion: int = 0
    unedited: Optional[Union[str, Id]] = None

MAX_CITATION = 40
def fallback_reply_to(replied: Message):
    if replied is None:
        return ""
    logging.debug(replied.dict())
    dt_object = datetime.utcfromtimestamp(replied.timestamp/1000) # in which timezone?
    msg_info = ""
    if len(replied.text) > 0:
        msg_info = replied.text[:MAX_CITATION]
        if len(replied.text) > MAX_CITATION:
            msg_info = msg_info + '...'
    else:
        msg_info = ""
        for el in replied.attachments:
            if msg_info != "":
                msg_info = msg_info + "| "
            msg_info = msg_info + el.name

    prefix = f"[{dt_object} UTC] > {msg_info}\n"
    logging.debug(prefix)
    return prefix

def fallback_forward(forwarded: Message):
    return fallback_reply_to(forwarded)

def fallback_attachment_caption(attachment: Attachment, only_format=False):
    if attachment.caption is None or attachment.caption == '':
        return ''
    name = attachment.name
    if only_format:
        if '.' in name:
            name = name[name.find('.'):]
        else:
            name = "file"
    res = f"|> {name}: {attachment.caption}\n"
    return res
