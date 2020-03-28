from common import API_URL, upsert_channel, remove_channel, add_attr_dict
import json

email_credentials = json.load(open('./email_credentials.json', 'r'))

CHANNEL = 'email'

test_upsert_channel_email = lambda: upsert_channel(CHANNEL, email_credentials)
test_remove_channel_email = lambda: remove_channel(CHANNEL, email_credentials)

class TestEmailClass:
    pass

email_default_thread_id = 'a.ishutin@sch-int.ru'

TestEmailClass = add_attr_dict(TestEmailClass, CHANNEL, email_credentials, email_default_thread_id)
