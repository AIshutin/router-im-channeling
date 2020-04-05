import requests
import copy
import random
import json
from common import API_URL, upsert_channel, remove_channel, add_attr_dict

TG_DC_ID = 1

tg_credentials = {'self_id': 0,
                  'phone': f'+99966{2}{str(random.randint(1,9))*4}',
                  'link': 'http://localhost:2000/_tg_get_code/2'}
tg_credentials = json.load(open('tg_credentials.json'))
# https://core.telegram.org/api/auth
CHANNEL = 'tg'

test_upsert_channel_tg = lambda: upsert_channel(CHANNEL, tg_credentials)
test_remove_channel_tg = lambda: remove_channel(CHANNEL, tg_credentials)

class TestTgClass:
    pass

TestTgClass = add_attr_dict(TestTgClass, CHANNEL, tg_credentials, "me")
