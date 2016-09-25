import time
from typing import List
from slackclient import SlackClient
import websockets
import asyncio
import ssl
import json

ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
ssl_context.load_verify_locations('/usr/local/etc/openssl/cert.pem')


class BetterSlack(SlackClient):
    def __init__(self, *args, **kwargs):
        SlackClient.__init__(self, *args, **kwargs)
        self.known_users = {}
        self._conn = None
        self.message_queue = []
        self._should_reconnect = False

    async def __aenter__(self):
        reply = self.server.api_requester.do(self.token, "rtm.start")
        if reply.status_code != 200:
            raise SlackConnectionError
        else:
            login_data = reply.json()
            if login_data["ok"]:
                self.ws_url = login_data['url']
                if not self._should_reconnect:
                    print('reconnecting..')
                    self.server.parse_slack_login_data(login_data)
                print('connecting', self.ws_url)
                self._conn = websockets.connect(self.ws_url, ssl=ssl_context)
                print('con', self._conn)
            else:
                raise SlackLoginError

        self.websocket = await self._conn.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._conn.__aexit__(*args, **kwargs)

    async def main_loop(self, parser=None, on_tick=None):
        async with self as self:
            while True:
                for message in self.message_queue:
                    await self.websocket.send(message)

                if parser is not None:
                    incoming = await self.get_message()
                    parser(incoming)
                if on_tick() is not None:
                    on_tick()
                asyncio.sleep(0.5)

    async def get_message(self):
        incoming = await self.websocket.recv()
        json_data = ""
        json_data += "{0}\n".format(incoming)
        json_data = json_data.rstrip()


        data = []
        if json_data != '':
            for d in json_data.split('\n'):
                data.append(json.loads(d))
        for item in data:
            self.process_changes(item)
        return data


    def send_to_websocket(self, data):
        """
        Send a JSON message directly to the websocket. See
        `RTM documentation <https://api.slack.com/rtm` for allowed types.

        :Args:
            data (dict) the key/values to send the websocket.

        """
        data = json.dumps(data)
        self.message_queue.append(data)

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
