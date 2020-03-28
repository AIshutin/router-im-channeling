from .common import Message, Channels, ChannelCredentials, gen_random_string, \
                    BASE_URL, SECRET_INTERNAL_KEY, MessageType, get_mime_type, \
                    save_b64_to_file, fallback_reply_to, fallback_forward, \
                    AttachmentType, fallback_attachment_caption
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
from email.message import EmailMessage
import email
import shutil
import smtplib
from email.mime.text import MIMEText

class EmailCredentials(pydantic.BaseModel):
    smpt: str
    password: str
    login: str
    imap: str

def send_message(message: Message, credentials: EmailCredentials, replied=Optional[Message]):
    msg = EmailMessage()
    text = message.text
    if message.forwarded is not None:
        for el in message.forwarded:
            text = fallback_forward(el) + text

    msg['Subject'] = message.email_subject
    msg['From'] = credentials.login
    msg['To'] = message.thread_id
    if replied is not None:
        msg['In-Reply-To'] = replied.original_ids[0]

    if message.attachments is not None:
        for el in message.attachments:
            fdir = f'/tmp/{gen_random_string()}'
            fname = fdir + f'/{el.name}'
            os.mkdir(fdir)
            save_b64_to_file(el.content, fname)
            maintype, subtype = get_mime_type(fname)
            msg.add_attachment(open(fname, 'rb').read(), maintype=maintype,
                                                        subtype=subtype,
                                                        filename=el.name)
            text = fallback_attachment_caption(el) + text
            shutil.rmtree(fdir)

    msg.attach(MIMEText(text))
    s = smtplib.SMTP(credentials.smpt, '587')
    s.starttls()
    s.login(credentials.login, credentials.password)
    res = s.send_message(msg)
    logging.debug(res)
    s.quit()
    return []

def add_channel(credentials: EmailCredentials):
    return ""

def remove_channel(credentials: EmailCredentials):
    pass
