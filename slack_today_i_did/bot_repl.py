from slack_today_i_did.bot_file import TodayIDidBot

import prompt_toolkit.layout.lexers
from prompt_toolkit.layout.lexers import Token
import prompt_toolkit.auto_suggest
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.shortcuts import (
    create_prompt_application,
    create_asyncio_eventloop,
    prompt_async,
    create_eventloop
)
from prompt_toolkit.history import FileHistory
from prompt_toolkit.contrib.completers import WordCompleter



class ReplBot(TodayIDidBot):
    def __init__(self, *args, **kwargs):
        TodayIDidBot.__init__(self, *args, **kwargs)
        self._setup_cli_history()

    def _setup_cli_history(self):
        self.cli_history = FileHistory('.cli_history')

    async def __aenter__(self):
        self.eventloop = create_asyncio_eventloop()
        self.completer = WordCompleter(self.known_tokens())

        config = {
            'complete_while_typing': True,
            'enable_history_search': True,
            'history': self.cli_history,
            'auto_suggest': Suggestions(),
            'completer': self.completer,
            'lexer': prompt_toolkit.layout.lexers.SimpleLexer()
        }

        self.cli = CommandLineInterface(
            application=create_prompt_application(f'{self.name} >>> ', **config),
            eventloop=self.eventloop
        )
        return self

    async def __aexit__(self, *args, **kwargs):
        return self

    async def get_message(self):
        incoming = await self.cli.run_async()
        incoming = f'<@{self.name}> {incoming.text}'

        data = [
            { "text": incoming
            , "type": "message"
            , "channel": "CLI"
            , "user": "CLI"
            }
        ]

        return data

    def ping(self):
        return self.send_to_websocket({"type": "ping"})

    def send_to_websocket(self, data):
        if 'type' not in data:
            return

        if data['type'] == 'message':
            print(data['text'])

    def set_known_users(self):
        return

    def user_name_from_id(self, my_id):
        for (name, id) in self.known_users.items():
            if id == my_id:
                return name
        return None

    def open_chat(self, name: str) -> str:
        return name

    def send_message(self, name: str, message: str) -> None:
        json = {"type": "message", "channel": id, "text": message}
        self.send_to_websocket(json)

    def send_channel_message(self, channel: str, message: str) -> None:
        json = {"type": "message", "channel": channel, "text": message}
        self.send_to_websocket(json)

    def connected_user(self, username: str) -> str:
        return username

    def attachment_strings(self, attachment):
        strings = []

        for (k, v) in attachment.items():
            if isinstance(v, str):
                strings.append(v)

        for field in attachment.get('fields', []):
            strings.append(field['title'])
            strings.append(field['value'])

        return strings



class Suggestions(prompt_toolkit.auto_suggest.AutoSuggestFromHistory):
    def get_suggestion(self, cli, buffer, document):
        return prompt_toolkit.auto_suggest.AutoSuggestFromHistory.get_suggestion(
            self,
            cli,
            buffer,
            document
        )
