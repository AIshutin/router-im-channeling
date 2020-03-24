import requests
import copy
from common import API_URL, TG_DEFAULT_THREAD_ID, upsert_channel, remove_channel, add_attr_dict

tg_bot_credentials = {'token': '801339101:AAH7GQKB5-XK0czIV9U6GzkafkC1Hq25o0o'}
CHANNEL = 'tg_bot'

test_upsert_channel_tg_bot = lambda: upsert_channel(CHANNEL, tg_bot_credentials)
test_remove_channel_tg_bot = lambda: remove_channel(CHANNEL, tg_bot_credentials)

class TestTgClass:
    pass

TestTgClass = add_attr_dict(TestTgClass, CHANNEL, tg_bot_credentials, TG_DEFAULT_THREAD_ID)
