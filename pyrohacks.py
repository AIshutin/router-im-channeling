import threading
from signal import signal, SIGINT, SIGTERM, SIGABRT
from pyrogram.client.types.user_and_chats.user import User
from pyrogram.errors import (
    PhoneMigrate, NetworkMigrate, SessionPasswordNeeded,
    FloodWait, PeerIdInvalid, VolumeLocNotFound, UserMigrate, ChannelPrivate, AuthBytesInvalid,
    BadRequest)
from pyrogram import Client
from pyrogram.client.types.authorization.terms_of_service import TermsOfService
import requests
import time

class NotNeeded(Exception):
    def __init__(self, desc=""):
        self.desc = desc
    def __str__(self):
        return f"{self.desc} is not needed and, thus, not implemented."

def custom_authorize(self):
    if self.bot_token:
        return self.sign_in_bot(self.bot_token)

    while True:
        try:
            if not self.phone_number:
                raise NotNeeded('command-line phone number')
            sent_code = self.send_code(self.phone_number)
        except BadRequest as e:
            print(e.MESSAGE)
            self.phone_number = None
            self.bot_token = None
        except FloodWait as e:
            print(e.MESSAGE.format(x=e.x))
            time.sleep(e.x)
        else:
            break

    if self.force_sms:
        sent_code = self.resend_code(self.phone_number, sent_code.phone_code_hash)

    print("The confirmation code has been sent via {}".format(
        {
            "app": "Telegram app",
            "sms": "SMS",
            "call": "phone call",
            "flash_call": "phone flash call"
        }[sent_code.type]
    ))

    while True:
        print(self.phone_code)
        if not self.phone_code:
            print(self._link)
            self.phone_code = requests.post(self._link, timeout=100).json()['code']
        else:
            print(f"Phone code: {self.phone_code}")
        print('...', self.phone_code)
        try:
            signed_in = self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
        except BadRequest as e:
            print(e.MESSAGE)
            self.phone_code = None
        except SessionPasswordNeeded as e:
            print(e.MESSAGE)

            while True:
                print("Password hint: {}".format(self.get_password_hint()))

                if not self.password:
                    raise NotNeeded('cli password form')
                try:
                    if not self.password:
                        raise NotNeeded('cloud password recovery')
                    else:
                        return self.check_password(self.password)
                except BadRequest as e:
                    print(e.MESSAGE)
                    self.password = None
                except FloodWait as e:
                    print(e.MESSAGE.format(x=e.x))
                    time.sleep(e.x)
        except FloodWait as e:
            print(e.MESSAGE.format(x=e.x))
            time.sleep(e.x)
        else:
            break

    if isinstance(signed_in, User):
        return signed_in

    print(signed_in)
    while True:
        first_name = 'Router.Im'
        last_name = 'Cerebra'

        try:
            signed_up = self.sign_up(
                self.phone_number,
                sent_code.phone_code_hash,
                first_name,
                last_name
            )
        except BadRequest as e:
            print(e.MESSAGE)
        except FloodWait as e:
            print(e.MESSAGE.format(x=e.x))
            time.sleep(e.x)
        else:
            break

    if isinstance(signed_in, TermsOfService):
        print("\n" + signed_in.text + "\n")
        self.accept_terms_of_service(signed_in.id)
    return signed_up

def idle(stop_signals: tuple = (SIGINT, SIGTERM, SIGABRT)):
    """Block the main script execution until a signal is received.
    This static method will run an infinite loop in order to block the main script execution and prevent it from
    exiting while having client(s) that are still running in the background.
    It is useful for event-driven application only, that are, applications which react upon incoming Telegram
    updates through handlers, rather than executing a set of methods sequentially.
    The way Pyrogram works, it will keep your handlers in a pool of worker threads, which are executed concurrently
    outside the main thread; calling idle() will ensure the client(s) will be kept alive by not letting the main
    script to end, until you decide to quit.
    Once a signal is received (e.g.: from CTRL+C) the inner infinite loop will break and your main script will
    continue. Don't forget to call :meth:`~Client.stop` for each running client before the script ends.
    Parameters:
        stop_signals (``tuple``, *optional*):
            Iterable containing signals the signal handler will listen to.
            Defaults to *(SIGINT, SIGTERM, SIGABRT)*.
    Example:
        .. code-block:: python
            :emphasize-lines: 13
            from pyrogram import Client
            app1 = Client("account1")
            app2 = Client("account2")
            app3 = Client("account3")
            ...  # Set handlers up
            app1.start()
            app2.start()
            app3.start()
            Client.idle()
            app1.stop()
            app2.stop()
            app3.stop()
    """

    def signal_handler(_, __):
        Client.is_idling = False

    if threading.current_thread() is threading.main_thread():
        for s in stop_signals:
            signal(s, signal_handler)

    Client.is_idling = True

    while Client.is_idling:
        time.sleep(1)
