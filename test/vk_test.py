import requests
import copy
from common import API_URL, TG_DEFAULT_THREAD_ID, upsert_channel, remove_channel, add_attr_dict

vk_credentials = {'token': '1895dbfc845d148eaf334224f661aa14d3cd641badb9eda096370d58efeca73e10d9a4040c9827d54c699',
                'self_id': '190503682'}
CHANNEL = 'vk'

test_upsert_channel_vk = lambda: upsert_channel(CHANNEL, vk_credentials)
test_remove_channel_vk = lambda: remove_channel(CHANNEL, vk_credentials)

class TestVkClass:
    pass

vk_default_thread_id = '421581863'

TestVkClass = add_attr_dict(TestVkClass, CHANNEL, vk_credentials, vk_default_thread_id)
