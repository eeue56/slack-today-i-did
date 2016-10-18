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
import slack_today_i_did.text_tools as text_tools


class GenericSlackBot(BetterSlack):
    _user_id = None
    _last_sender = None

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
            'func-that-return': self.functions_that_return,
            'error-help': self.error_help,
            'help': self.help,
            'possible-funcs': self.possible_funcs,
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

    def parse(self, text, channel):
        """ Take text, a default channel,
        """

        # we only tokenize those that talk to me
        if self.was_directed_at_me(text):
            text = text.lstrip(f'<@{self.user_id}>').strip()
        else:
            return None

        # we always give the channel as the first arg
        args = [parser.Constant(channel, str)]
        tokens = parser.tokenize(text, self.known_tokens())
        return parser.parse(tokens, self.known_functions(), default_args=args)

    def _actually_parse_message(self, message):
        channel = message['channel']
        text = message['text']

        stuff = self.parse(text, channel)

        if stuff is None:
            return

        action = stuff['action']
        args = stuff['args']
        evaluate = stuff['evaluate']

        annotations = copy.deepcopy(action.__annotations__)
        annotations.pop('return')
        error_messages = []

        # check arity mismatch
        num_keyword_args = len(action.__defaults__) if action.__defaults__ else 0
        num_positional_args = len(annotations) - num_keyword_args
        if num_positional_args > len(args):
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

        eval_result = evaluate(args)

        # deal with exceptions running the command
        if len(eval_result['errors']) > 0:
            messages = parser.exception_error_messages(eval_result['errors'])
            self.send_channel_message(channel, '\n\n'.join(messages))
            return

        if action != self.known_statements()['!!']:
            self.command_history.add_command(channel, action, eval_result['args'])

        try:
            action(*eval_result['args'])
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

        if stuff is None:
            self.send_channel_message(channel, 'No commands have been run yet!')
            return

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

    def possible_funcs(self, channel: str, name: str) -> None:
        """ give me a name and I'll tell you funcs which are close """

        known_functions = self.known_functions()

        # default the length of the name
        acceptable_score = len(name)

        # but for long names, we want to cap it a bit
        if acceptable_score > 10:
            acceptable_score = 10
        elif acceptable_score > 5:
            acceptable_score = 4

        possibles = possible_functions(known_functions, name, acceptable_score=acceptable_score)

        if len(possibles) == 0:
            self.send_channel_message(channel, "I don't know what you mean and have no suggestions")
            return

        message = f'I don\'t know about `{name}`. But I did find the following functions with similiar names:\n'
        message += ' | '.join(possibles[:5])

        self.send_channel_message(channel, message)

    @parser.metafunc
    def help(self, channel: str, args: List[parser.TopLevelArg]) -> None:
        """ given a function name, I'll tell you about it
        """
        if not len(args):
            self.list(channel)
            return

        if isinstance(args[0], parser.Constant):
            func_name = args[0].value
        else:
            func_name = args[0].func_name
        known_functions = self.known_functions()

        if func_name not in known_functions:
            return self.possible_funcs(channel, func_name)

        func = known_functions[func_name]
        docs = ' '.join(line.strip() for line in func.__doc__.split('\n'))

        message = f'`{func_name}` has the help message:\n{docs}\n'

        if not parser.is_metafunc(func):
            message += 'And the type info:\n```\n'

            type_info = '\n'.join(
                f'- {arg_name} : {arg_type}'
                for (arg_name, arg_type) in func.__annotations__.items()
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


def possible_functions(known_functions, name, acceptable_score=5):
    possibles = [
        (text_tools.token_based_levenshtein(func_name, name), func_name) for func_name in known_functions
    ]

    possibles = [x for x in possibles if x[0] < acceptable_score]
    possibles = sorted(possibles, key=lambda x: x[0])
    possibles = [x[1] for x in possibles]

    return possibles


class BotExtension(GenericSlackBot):
    def __init__(self, *args, **kwargs):
        pass
