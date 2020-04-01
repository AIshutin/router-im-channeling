import requests
import copy
from common import API_URL, upsert_channel, remove_channel, TG_DEFAULT_THREAD_ID

TG_DC_ID = 1

tg_credentials = {'self_id': TG_DEFAULT_THREAD_ID,
                  'link': f'{API_URL}/_tg_get_code/{TG_DC_ID}',
                  'phone': f'+99966{TG_DC_ID}{1555}'}
# https://core.telegram.org/api/auth
CHANNEL = 'tg'

test_upsert_channel_tg = lambda: upsert_channel(CHANNEL, tg_credentials)
test_remove_channel_tg = lambda: remove_channel(CHANNEL, tg_credentials)
