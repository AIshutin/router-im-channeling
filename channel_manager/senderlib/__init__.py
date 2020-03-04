from .common import Channels, ChannelCredentials, Message
from .tg import add_channel as tg_add_channel
from .tg import send_message as tg_send_message
from .tg import remove_channel as tg_remove_channel

def send_message(channel: Channels, message: Message,
        credentials: ChannelCredentials):
    return globals()[f'{channel}_send_message'](message, credentials)

def add_channel(channel: Channels, credentials: ChannelCredentials):
    return globals()[f'{channel}_add_channel'](credentials)
    #return getattr(getattr(globals(), channel), 'add_channel')(credentials)

def remove_channel(channel: Channels, credentials: ChannelCredentials):
    return globals()[f'{channel}_remove_channel'](credentials)
