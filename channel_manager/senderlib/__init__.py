from .common import Channels, ChannelCredentials, Message

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

def send_message(channel: Channels, message: Message, credentials):
    credentials = globals()[f'{channel}credentials'](**credentials)
    return globals()[f'{channel}_send_message'](message, credentials)

def add_channel(channel: Channels, credentials) -> str:
    return globals()[f'{channel}_add_channel'](credentials)
    #return getattr(getattr(globals(), channel), 'add_channel')(credentials)

def remove_channel(channel, credentials):
    credentials = globals()[f'{channel}credentials'](**credentials)
    return globals()[f'{channel}_remove_channel'](credentials)
