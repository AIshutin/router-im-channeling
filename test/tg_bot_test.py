import requests
import copy
from common import API_URL, text_message, TG_DEFAULT_THREAD_ID

tg_bot_credentials = {'token': '801339101:AAH7GQKB5-XK0czIV9U6GzkafkC1Hq25o0o'}


def test_upsert_channel_tg_bot():
    url = f"{API_URL}/upsert_channel/tg_bot"
    resp = requests.post(url, json={'credentials': tg_bot_credentials})
    assert(resp.status_code == 200)
    data = resp.json()
    assert('channel_id' in data and len(data['channel_id']) > 0)
    return data['channel_id']

def test_remove_channel_tg_bot(channel_id=None):
    if channel_id is None:
        channel_id = test_upsert_channel_tg_bot()
    url = f"{API_URL}/remove_channel"
    resp = requests.post(url, json={'channel_id': channel_id})
    assert(resp.status_code == 200)

def test_send_text_message_tg_bot():
    channel_id = test_upsert_channel_tg_bot()
    message = copy.deepcopy(text_message)
    message['channel_id'] = channel_id
    message['thread_id'] = TG_DEFAULT_THREAD_ID
    url = f"{API_URL}/send_message"
    resp = requests.post(url, json={'message': message})
    assert(resp.status_code == 200)
    data =resp.json()
    assert('id' in data and len(data['id']) != 0)
    assert('original_ids' in data and len(data['original_ids']) != 0)
    assert('server_timestamp' in data and data['server_timestamp'] > 1e12)
    test_remove_channel_tg_bot(channel_id)

def test_duplicate_upsertion():
    resp1 = test_upsert_channel_tg_bot()
    resp2 = test_upsert_channel_tg_bot()
    assert(resp1 == resp2)
