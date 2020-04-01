import requests
import copy
import random
import json
from common import API_URL, upsert_channel, remove_channel, TG_DEFAULT_THREAD_ID

TG_DC_ID = 1

tg_credentials = json.load(open('tg_credentials.json'))
# https://core.telegram.org/api/auth
CHANNEL = 'tg'

test_upsert_channel_tg = lambda: upsert_channel(CHANNEL, tg_credentials)
test_remove_channel_tg = lambda: remove_channel(CHANNEL, tg_credentials)
