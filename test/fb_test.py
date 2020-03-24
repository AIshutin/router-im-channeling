import requests
import copy
from common import API_URL, TG_DEFAULT_THREAD_ID, upsert_channel, remove_channel, add_attr_dict

fb_credentials = {'self_id': '101962504709802',
                  'token': 'EAAIrF0hyVy0BALNlqxTKXsUC2YUnT4GzDMdG6LsYmVIO0y1ocBNcWHzrs26GYWDQr8m5A9aMMjGZBqzYtywW8JmWuAi0DGhGJGeeZA0kz5XCC6u2ptiRPaqfYbu9MRrZCn34JHWAbuFokGJ3E4Fpdjg1ERrSO2M2gkhzoSonwZDZD'}

CHANNEL = 'fb'

test_upsert_channel_fb = lambda: upsert_channel(CHANNEL, fb_credentials)
test_remove_channel_fb = lambda: remove_channel(CHANNEL, fb_credentials)

class TestFbClass:
    pass

fb_default_thread_id = '2673203139464950'

TestFbClass = add_attr_dict(TestFbClass, CHANNEL, fb_credentials, fb_default_thread_id)
