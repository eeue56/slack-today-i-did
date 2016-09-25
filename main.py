import time
from slackclient import SlackClient
from better_slack import BetterSlack
import json
import time
from typing import List, Tuple
import datetime
import copy
import html
import asyncio


class TodayIDidBot(BetterSlack):
    def __init__(self, *args, **kwargs):
        BetterSlack.__init__(self, *args, **kwargs)
        self.reports = {}
        self._user_id = None
        self.name = 'today-i-did'

    def is_direct_message(self, message):
        return message['channel'].startswith('D')

    def parse_direct_message(self, message):
        user = message['user']
        text = message['text']
        name = self.user_name_from_id(user)
        print(user, text)

        for (channel_name, reports) in self.reports.items():
            for report in reports:
                if report.is_for_user(name):
                    report.add_response(name, text)
                    self.send_message(name, 'Thanks!')

    def parse_message(self, message):
        if ('type' not in message or 'text' not in message):
            return None

        if message['type'] != 'message':
            return None

        if self.is_direct_message(message):
            return self.parse_direct_message(message)

        channel = message['channel']


        text = message['text']

        stuff = self.tokenize(text, channel)

        if stuff is None:
            return

        action = stuff['action']
        args = stuff['args']
        errors = stuff['errors']

        # validate the command
        annotations = copy.deepcopy(action.__annotations__)
        annotations.pop('return')
        error = False

        # deal with exceptions running the command
        if len(errors) > 0:
            message = f'I got the following errors:\n'
            message += '```\n'
            message += '\n'.join(f'- {func_name} threw {error}' for (func_name, error) in errors)
            message += '\n```'

            self.send_channel_message(channel, message)
            error = True

        # deal with mistmachting args
        if len(annotations) != len(args):
            message = f'I wanted things to look like for function `{action.__name__}`:\n'
            message += '```\n'
            message = message + '\n'.join(f'- {arg_name} : {type}' for (arg_name, type) in annotations.items())
            message += '\n```'

            message = message + "\nBut you gave me:\n"
            message += '```\n'
            message = message + '\n'.join(f'- {arg} : {type}' for (arg, type) in args)
            message += '\n```'

            if len(annotations) < len(args):
                self.send_channel_message(channel, 'too many args too many many args\n' + message)
            else:
                self.send_channel_message(channel, 'we need some more args in here! we need some more args in here\n' + message)


            error = True

        # deal with mistmachting types
        for ((arg, type), (arg_name, annotation)) in zip(args, annotations.items()):
            if type != annotation:
                message = f'Type mistmach for function `{action.__name__}`\n'
                message += f'You tried to give me a `{type}` but I wanted a `{annotation}` for the arg `{arg_name}`!'

                self.send_channel_message(channel, message)
                error = True

        if error:
            return

        func_args = [arg[0] for arg in args]
        action(*func_args)

    def parse_messages(self, messages):
        for message in messages:
            print(message)
            self.parse_message(message)

    async def main_loop(self):
        await BetterSlack.main_loop(self, parser=self.parse_messages, on_tick=self.on_tick)

    @property
    def user_id(self):
        if self._user_id is None:
            data = self.connected_user(self.name)
            self._user_id = data

        return self._user_id

    def on_tick(self):
        for (channel, reports) in self.reports.items():
            for report in reports:
                if report.is_time_to_bother_people():
                    report.bother_people(self)
                elif report.is_time_to_end():
                    self.single_report_responses(channel, report)


    def add_report(self, report):
        if report.channel not in self.reports:
            self.reports[report.channel] = []
        self.reports[report.channel].append(report)

    def was_directed_at_me(self, text):
        return text.startswith(f'<@{self.user_id}>')

    def tokenize(self, text, channel):
        """
            at_statement: 'AT' NAME [ arg ]
            for_statement: 'FOR' NAME [ arg ]
            func_name: NAME
            arg: at_statement | for_statement | ENDMARKER
            arglist: arg
            single_input: func_name arg ENDMARKER
        """

        text = text.strip()

        # we only tokenize those that talk to me
        if self.was_directed_at_me(text):
            text = text.lstrip(f'<@{self.user_id}>').strip()
        else:
            return None

        # we always give the channel as the first arg
        args = [ (channel, str) ]


        tokens = self.fill_in_the_gaps(text, self.tokens_with_index(text))
        print('tokens', tokens)

        errors = []

        # when we can't find anything
        if len(tokens) == 0:
            first_function_name = 'error-help'
            args.append(('NO_TOKENS', str))
        # when we have stuff to work with!
        else:
            first_function_name = tokens[0][1]
            first_arg = tokens[0][2].strip()

            if len(first_arg) > 0:
                args.append((first_arg, str))

            if len(tokens) > 1:
                for (start_index, function_name, arg_to_function) in tokens[1:]:
                    func = self.known_functions[function_name]

                    try:
                        evaled = func(arg_to_function)
                        args.append((evaled, func.__annotations__.get('return', None)))
                    except Exception as e:
                        errors.append((function_name, e))

        return {
            'action': self.known_functions[first_function_name],
            'args' : args,
            'errors': errors
        }

    def fill_in_the_gaps(self, message, tokens):
        """
            take things that look like [(12, FOR)] turn into [(12, FOR, noah)]
        """

        if len(tokens) < 1:
            return []

        if len(tokens) == 1:
            start_index = tokens[0][0]
            token = tokens[0][1]

            return [ (start_index, token, message[start_index + len(token) + 1:]) ]

        builds = []

        for (i, (start_index, token)) in enumerate(tokens):
            if i == len(tokens) - 1:
                builds.append((start_index, token, message[start_index + len(token) + 1:]))
                continue


            end_index = tokens[i + 1][0]
            builds.append((start_index, token, message[start_index + len(token) + 1: end_index]))

        return builds


    def tokens_with_index(self, message):
        """ get the tokens out of a message, in order, along with
            the index it was found at
        """

        build = []

        start_index = 0
        end_index = 0
        offset = 0

        for word in message.split(' '):
            if word in self.known_tokens:
                token = word
                start_index = end_index + message[end_index:].index(token)
                end_index = start_index + len(token)
                build.append((start_index, token))

        return sorted(build, key=lambda x:x[0])

    def for_statement(self, text: str) -> List[str]:
        """ enter usernames seperated by commas """
        return [blob.strip() for blob in text.split(',')]

    def at_statement(self, text: str) -> datetime.datetime:
        """ enter a time in the format HH:MM """
        return datetime.datetime.strptime(text.strip(), '%H:%M')

    def wait_statement(self, text: str) -> datetime.datetime:
        """ enter how much time to wait in the format HH:MM """
        return datetime.datetime.strptime(text.strip(), '%H:%M')

    @property
    def known_tokens(self) -> List[str]:
        return list(self.known_functions.keys())

    @property
    def known_functions(self):
        return {
            'bother' : self.bother,
            'bother-all-now' : self.bother_all_now,
            'func-that-return' : self.functions_that_return,
            'error-help' : self.error_help,
            'help' : self.help,
            'responses' : self.responses,
            'FOR' : self.for_statement,
            'AT' : self.at_statement,
            'WAIT' : self.wait_statement
        }

    def help(self, channel: str, func_name: str) -> None:
        """ given a func_name preceeded with `~`, I'll tell you about it
        """
        func_name = func_name.strip()[1:]
        func = self.known_functions[func_name]
        docs = ' '.join(line.strip() for line in func.__doc__.split('\n'))

        message = f'`{func_name}` has the help message:\n{docs}\nAnd the type info:\n'
        message += '```\n'

        type_info = '\n'.join(f'- {arg_name} : {type}' for (arg_name, type) in func.__annotations__.items())

        message += f'{type_info}\n```'

        self.send_channel_message(channel, message)

    def responses(self, channel: str) -> None:
        """ list the last report responses for the current channel """

        if channel not in self.reports:
            self.send_channel_message(channel, f'No reports found for channel {channel}')
            return

        message = ""
        for report in self.reports[channel]:
            message += '\n\n'.join(f'User {user} responded with:\n{response}' for (user, response) in report.responses.items())

        self.send_channel_message(channel, message)

    def single_report_responses(self, channel: str, report) -> None:
        message = '\n\n'.join(f'User {user} responded with:\n{response}' for (user, response) in report.responses.items())
        self.send_channel_message(channel, message)


    def bother(self, channel: str, users: List[str], at: datetime.datetime, wait: datetime.datetime) -> None:
        """ add a report for the given users at a given time,
            reporting back in the channel requested
        """
        time_to_run = (at.hour, at.minute)
        wait_for = (wait.hour, wait.minute)
        self.add_report(Report(channel, time_to_run, users, wait_for))

    def bother_all_now(self, channel: str) -> None:
        """ run all the reports for a channel
        """
        for report in self.reports.get(channel, []):
            report.bother_people(self)

    def error_help(self, channel: str, problem: str) -> None:
        """ present an error help message """
        if problem == 'NO_TOKENS':
            self.send_channel_message(channel, 'I\'m sorry, I couldn\'t find any tokens.')
        else:
            self.send_channel_message(channel, f'Some problem: {problem}')

    def functions_that_return(self, channel:str, text: str) -> None:
        """ give a type, return functions that return things of that type
        """
        func_names = []
        text = text.strip()
        text = html.unescape(text)

        for (name, func) in self.known_functions.items():
            if str(func.__annotations__.get('return', None)) == text:
                func_names.append((name, func.__annotations__))

        message = f"The following functions return `{text}`:\n"
        message += '```\n'
        message += '\n'.join(name for (name, type) in func_names)
        message +='\n```'

        self.send_channel_message(channel, message)




class Report(object):
    def __init__(self, channel, time_to_run: Tuple[int,int], people, wait: Tuple[int, int], time_run=None):
        self.people_to_bother = people
        self.channel = channel
        self.responses = {}
        self.time_run = time_run
        self.wait_for = wait
        self.time_to_run = time_to_run
        self.is_ended = False

    def bother_people(self, client):
        if not self.people_to_bother:
            return

        self.time_run = datetime.datetime.utcnow()
        client.send_channel_message(self.channel, 'Starting my report!')
        for person in self.people_to_bother[:]:
            client.send_message(person, 'Sorry to bother you!')
            self.add_response(person, '')
            self.people_to_bother.remove(person)

    def is_time_to_bother_people(self) -> bool:
        if not self.people_to_bother:
            return False
        current_time = time.time()
        time_now = time.strftime("%H:%M:", time.gmtime(current_time))
        time_now = (int(time_now.split(':')[0]), int(time_now.split(':')[1]))

        if time_now < self.time_to_run:
            return False

        self.is_ended = False
        return True

    def is_time_to_end(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now = time.strftime("%H:%M:", time.gmtime(current_time))
        time_now = (int(time_now.split(':')[0]), int(time_now.split(':')[1]))

        if time_now < (self.time_to_run[0] + self.wait_for[0], self.time_to_run[1] + self.wait_for[1]):
            return False

        self.is_ended = True
        return True

    def is_for_user(self, user):
        return user in self.responses or user in self.people_to_bother

    def add_response(self, user, message):
        if user not in self.responses:
            self.responses[user] = message
        else:
            if len(self.responses[user]) == 0:
                self.responses[user] = message
            else:
                self.responses[user] += '\n' + message

    def as_dict(self):
        return {
            'channel' : self.channel,
            'responses' : self.responses,
            'people_to_bother' : self.people_to_bother,
            'time_run' : (str(self.time_run) if self.time_run is not None else "")
        }





def setup():
    with open('priv.json') as f:
        data = json.load(f)

    return TodayIDidBot(data['token'])

def main():
    client = setup()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main_loop())


if __name__ == '__main__':
    main()
