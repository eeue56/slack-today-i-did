"""
A slack client with much better async support
"""

from slackclient import SlackClient
import websockets
import asyncio
import ssl
import json

ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

# os x stores ssl certs in a strange place, so this fixes the openssl cert import
try:
    ssl_context.load_verify_locations('/usr/local/etc/openssl/cert.pem')
except Exception:
    pass


# we need to redefine these because the slackclient library is bad
class SlackLoginError(Exception):
    pass


class SlackConnectionError(Exception):
    pass


class BetterSlack(SlackClient):
    """ a better slack client with async/await support """

    def __init__(self, *args, **kwargs):
        SlackClient.__init__(self, *args, **kwargs)
        self.known_users = {}
        self._conn = None
        self.message_queue = []
        self._should_reconnect = False
        self._in_count = 0

    async def __aenter__(self):
        reply = self.server.api_requester.do(self.token, "rtm.connect")

        if reply.status_code != 200:
            raise SlackConnectionError
        else:
            print('Connected okay')
            login_data = reply.json()

            if login_data["ok"]:
                self.ws_url = login_data['url']
                self._conn = websockets.connect(self.ws_url, ssl=ssl_context, timeout=30, max_size=2 ** 30)
                print('Made websocket connection')
                if not self._should_reconnect:
                    self.login_data = login_data
                    self.domain = self.login_data["team"]["domain"]
                    self.username = self.login_data["self"]["name"]
                print('Parsed log in data..')
            else:
                print('Failed to connect..')
                raise SlackLoginError

        self.websocket = await self._conn.__aenter__()
        print('Starting main loop..')
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._conn.__aexit__(*args, **kwargs)

    async def main_loop(self, parser=None, on_tick=None):
        async with self as self:
            while True:
                while len(self.message_queue) > 0:
                    await self.websocket.send(self.message_queue.pop(0))

                if parser is not None:
                    incoming = await self.get_message()
                    try:
                        parser(incoming)
                    except Exception as e:
                        print(f'Error: {e}')
                if on_tick() is not None:
                    on_tick()
                self._in_count += 1

                if self._in_count > (0.5 * 60 * 3):
                    self.ping()
                    self._in_count = 0

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

    def ping(self):
        return self.send_to_websocket({"type": "ping"})

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

    def send_message(self, name: str, message: str) -> None:
        id = self.open_chat(name)

        json = {"type": "message", "channel": id, "text": message}
        self.send_to_websocket(json)

    def send_channel_message(self, channel: str, message: str) -> None:
        json = {"type": "message", "channel": channel, "text": message}
        self.send_to_websocket(json)

    def send_threaded_message(self, channel: str, time_stamp: str, message: str) -> None:
        json = {"type": "message", "channel": channel, "text": message, "thread_ts": time_stamp}
        self.send_to_websocket(json)

    def get_channel_info(self, channel: str) -> None:
        channel_info = self.api_call('channels.info', channel=channel)

        return channel_info

    def get_user_info(self, user_id: str) -> None:
        user_info = self.api_call('users.info', user=user_id)

        return user_info

    def connected_user(self, username: str) -> str:
        if username not in self.known_users:
            self.set_known_users()

        return self.known_users[username]

    def attachment_strings(self, attachment):
        strings = []

        for (k, v) in attachment.items():
            if isinstance(v, str):
                strings.append(v)

        for field in attachment.get('fields', []):
            strings.append(field['title'])
            strings.append(field['value'])

        return strings
