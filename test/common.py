import os
API_URL = os.getenv('API_URL', "http://localhost:2000")

text_message = {'mtype': 'message',
                'text': 'hello_world!',
                'author': 'Bob',
                'author_name': 'Bob Sanderson',
                'author_type': 'agent',
                }
TG_DEFAULT_THREAD_ID = os.getenv('TG_DEFAULT_THREAD_ID', '438162308')
