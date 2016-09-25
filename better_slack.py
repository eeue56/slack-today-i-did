import time
from typing import List
from slackclient import SlackClient

class BetterSlack(SlackClient):
    def __init__(self, *args, **kwargs):
        SlackClient.__init__(self, *args, **kwargs)
        self.known_users = {}

    def set_known_users(self):
        response = self.api_call('users.list')

        if not response['ok']:
            return

        for member in response['members']:
            self.known_users[member['name']] = member['id']

    def user_name_from_id(self, my_id):
        for (name, id) in self.known_users.items():
            if id == my_id:
                return name
        return None

    def open_chat(self, name: str) -> str:
        if name not in self.known_users:
            self.set_known_users()

        person = self.known_users[name]
        response = self.api_call('im.open', user=person)

        return response['channel']['id']


    def send_message(self, name, message) -> None:
        id = self.open_chat(name)

        self.rtm_send_message(id, message)

    def send_channel_message(self, channel, message) -> None:
        self.api_call('chat.postMessage', channel=channel, text=message)

    def connected_user(self, username):
        if username not in self.known_users:
            self.set_known_users()

        return self.known_users[username]


    def main_loop(self, parser=None, on_tick=None):
        connected = self.rtm_connect()
        if not connected:
            raise Exception('Connection failed!')

        while True:
            if parser is not None:
                parser(self.rtm_read())
            if on_tick() is not None:
                on_tick()
            time.sleep(0.5)
