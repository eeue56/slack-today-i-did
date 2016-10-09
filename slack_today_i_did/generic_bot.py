"""
This file contains the bot itself

To add a new function:
    - add an entry in `known_functions`. The key is the command the bot
        will know, the value is the command to run
    - You must add type annotitions for the bot to match args up correctly

"""

import copy
import html

from typing import List

from slack_today_i_did.better_slack import BetterSlack
from slack_today_i_did.command_history import CommandHistory

import slack_today_i_did.self_aware as self_aware

import slack_today_i_did.parser as parser


class GenericSlackBot(BetterSlack):
    def __init__(self, *args, **kwargs):
        BetterSlack.__init__(self, *args, **kwargs)
        self.name = 'generic-slack-bot'

        self.command_history = CommandHistory()

    def is_direct_message(self, channel):
        """ Direct messages start with `D`
        """
        return channel.startswith('D')

    def was_directed_at_me(self, text):
        return text.startswith(f'<@{self.user_id}>')

    def parse_direct_message(self, message):
        self._actually_parse_message(message)

    async def main_loop(self):
        await BetterSlack.main_loop(
            self,
            parser=self.parse_messages,
            on_tick=self.on_tick
        )

    def known_tokens(self) -> List[str]:
        return list(self.known_functions().keys())

    def known_functions(self):
        return {**self.known_user_functions(), **self.known_statements()}

    def known_user_functions(self):
        return {
            'bother-all-now': self.bother_all_now,
            'func-that-return': self.functions_that_return,
            'error-help': self.error_help,
            'help': self.help,
            'list': self.list,
            'reload-funcs': self.reload_functions,
        }

    def known_statements(self):
        return {
            '!!': self.last_command_statement
        }

    def on_tick(self):
        pass

    @property
    def user_id(self):
        if self._user_id is None:
            data = self.connected_user(self.name)
            self._user_id = data

        return self._user_id

    def tokenize(self, text, channel):
        """ Take text, a default channel,
        """

        # we only tokenize those that talk to me
        if self.was_directed_at_me(text):
            text = text.lstrip(f'<@{self.user_id}>').strip()
        else:
            return None

        # we always give the channel as the first arg
        tokens = parser.tokenize(text, self.known_tokens())
        args = [(channel, str)]

        return parser.eval(tokens, self.known_functions(), default_args=args)

    def _actually_parse_message(self, message):
        channel = message['channel']
        text = message['text']

        stuff = self.tokenize(text, channel)

        if stuff is None:
            return

        action = stuff['action']
        args = stuff['args']
        errors = stuff.get('errors', [])

        annotations = copy.deepcopy(action.__annotations__)
        annotations.pop('return')
        error_messages = []

        # deal with exceptions running the command
        if len(errors) > 0:
            error_messages.append(parser.exception_error_messages(errors))

        if len(annotations) != len(args):
            error_messages.append(
                parser.mismatching_args_messages(action, annotations, args)
            )

        mismatching_types = parser.mismatching_types_messages(
            action,
            annotations,
            args
        )

        if len(mismatching_types) > 0:
            error_messages.append(mismatching_types)

        if len(error_messages) > 0:
            self.send_channel_message(channel, '\n\n'.join(error_messages))
            return

        func_args = [arg[0] for arg in args]

        if action != self.known_statements()['!!']:
            self.command_history.add_command(channel, action, func_args)

        try:
            action(*func_args)
        except Exception as e:
            self.send_channel_message(channel, f'We got an error {e}!')

    def parse_message(self, message):
        # if we don't have any of the useful data, return early

        if 'type' not in message or 'text' not in message:
            return None

        if message['type'] != 'message':
            return None

        self._last_sender = message.get('user', None)

        # if it's a direct message, parse it differently
        if self.is_direct_message(message['channel']):
            return self.parse_direct_message(message)

        return self._actually_parse_message(message)

    def parse_messages(self, messages):
        for message in messages:
            print(message)
            self.parse_message(message)

    def error_help(self, channel: str, problem: str) -> None:
        """ present an error help message """
        if problem == 'NO_TOKENS':
            self.send_channel_message(channel, 'I\'m sorry, I couldn\'t find any tokens. Try using `help` or `list`')  # noqa: E501
        else:
            self.send_channel_message(channel, f'Some problem: {problem}')

    def last_command_statement(self, channel: str) -> None:
        """ run the last command again """

        stuff = self.command_history.last_command(channel)
        action = stuff['action']
        args = stuff['args']

        action(*args)

    def list(self, channel: str) -> None:
        """ list known statements and functions """

        message = 'Main functions:\n'
        message += '\n'.join(
            f'`{func}`'for func in self.known_user_functions()
        )

        message += '\nStatements:\n'
        message += '\n'.join(
            f'`{func}`'for func in self.known_statements()
        )

        self.send_channel_message(channel, message)

    def help(self, channel: str, func_name: str) -> None:
        """ given a func_name preceeded with `~`, I'll tell you about it
        """
        func_name = func_name.strip()[1:]
        func = self.known_functions()[func_name]
        docs = ' '.join(line.strip() for line in func.__doc__.split('\n'))

        message = f'`{func_name}` has the help message:\n{docs}\nAnd the type info:\n'  # noqa: E501
        message += '```\n'

        type_info = '\n'.join(
            f'- {arg_name} : {type}' for (arg_name, type) in func.__annotations__.items()  # noqa: E501
        )

        message += f'{type_info}\n```'

        self.send_channel_message(channel, message)

    def reload_functions(self, channel: str) -> None:
        """ reload the functions a bot knows """
        self_aware.restart_program()

    def functions_that_return(self, channel: str, text: str) -> None:
        """ give a type, return functions that return things of that type
        """
        func_names = []
        text = text.strip()
        text = html.unescape(text)

        for (name, func) in self.known_functions().items():
            if str(func.__annotations__.get('return', None)) == text:
                func_names.append((name, func.__annotations__))

        message = f"The following functions return `{text}`:\n"
        message += '```\n'
        message += '\n'.join(name for (name, type) in func_names)
        message += '\n```'

        self.send_channel_message(channel, message)
