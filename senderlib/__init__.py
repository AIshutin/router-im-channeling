from .common import Channels, ChannelCredentials, Message

from .tg_bot import add_channel as tg_bot_add_channel
from .tg_bot import send_message as tg_bot_send_message
from .tg_bot import remove_channel as tg_bot_remove_channel
from .tg_bot import TgCredentials as tg_botcredentials

from .tg import add_channel as tg_add_channel
from .tg import send_message as tg_send_message
from .tg import remove_channel as tg_remove_channel
from .tg import TgCredentials as tgcredentials

from .fb import add_channel as fb_add_channel
from .fb import send_message as fb_send_message
from .fb import remove_channel as fb_remove_channel
from .fb import FbCredentials as fbcredentials

from .vk import add_channel as vk_add_channel
from .vk import send_message as vk_send_message
from .vk import remove_channel as vk_remove_channel
from .vk import VkCredentials as vkcredentials

from .mail import add_channel as email_add_channel
from .mail import send_message as email_send_message
from .mail import remove_channel as email_remove_channel
from .mail import EmailCredentials as emailcredentials

from pydantic import BaseModel
from typing import Optional, List, Union

def send_message(channel: Channels, message: Message, credentials, \
            replied: Optional[Message]=None, specific: Optional[dict]=None) -> str:
    credentials = globals()[f'{channel}credentials'](**credentials)
    return globals()[f'{channel}_send_message'](message, credentials, \
                                            replied=replied, specific=specific)

def add_channel(channel: Channels, credentials) -> str:
    return globals()[f'{channel}_add_channel'](credentials)
    #return getattr(getattr(globals(), channel), 'add_channel')(credentials)

def remove_channel(channel, credentials):
    credentials = globals()[f'{channel}credentials'](**credentials)
    return globals()[f'{channel}_remove_channel'](credentials)

class Credentials(BaseModel):
    channel_type: Channels
    webhook_token: str
    timestamp: Optional[str] = None
    credentials: Union[fbcredentials, vkcredentials, tg_botcredentials, \
                        emailcredentials, tgcredentials]
