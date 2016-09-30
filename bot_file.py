"""
This file contains the bot itself

To add a new function:
    - add an entry in `known_functions`. The key is the command the bot will know, the value is the command to run
    - You must add type annotitions for the bot to match args up correctly

"""

import time
import datetime
from slackclient import SlackClient
from better_slack import BetterSlack
from rollbar import Rollbar
from typing import List, Tuple
import types
import copy
import html
import json


class CommandHistory(object):
    def __init__(self):
        self.history = {}

    def add_command(self, channel, command, args):
        if channel not in self.history:
            self.history[channel] = []

        self.history[channel].append({ 'action': command, 'args': args })

    def last_command(self, channel):
        if channel not in self.history:
            return None
        return self.history[channel][-1]



class TodayIDidBot(BetterSlack):
    def __init__(self, *args, **kwargs):
        if 'rollbar_token' in kwargs:
            self.rollbar = Rollbar(kwargs.pop('rollbar_token'))
        else:
            self.rollbar = None

        if 'elm_repo' in kwargs:
            self.repo = kwargs.pop('elm_repo')
        else:
            self.repo = None

        BetterSlack.__init__(self, *args, **kwargs)
        self.reports = {}
        self._user_id = None
        self.name = 'today-i-did'

        self.command_history = CommandHistory()

    def is_direct_message(self, message):
        return message['channel'].startswith('D')

    def parse_direct_message(self, message):
        user = message['user']
        text = message['text']
        name = self.user_name_from_id(user)

        for (channel_name, reports) in self.reports.items():
            for report in reports.values():
                if report.is_for_user(name):
                    report.add_response(name, text)
                    self.send_message(name, 'Thanks!')

    def _deal_with_exceptions(self, channel, errors):
        message = f'I got the following errors:\n'
        message += '```\n'
        message += '\n'.join(f'- {func_name} threw {error}' for (func_name, error) in errors)
        message += '\n```'

        self.send_channel_message(channel, message)

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
        errors = stuff.get('errors', [])



        # validate the command
        annotations = copy.deepcopy(action.__annotations__)
        annotations.pop('return')
        error = False

        # deal with exceptions running the command
        if len(errors) > 0:
            self._deal_with_exceptions(channel, errors)
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

        if action != self.known_statements()['!!']:
            self.command_history.add_command(channel, action, func_args)

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
            for report in reports.values():
                if report.is_time_to_bother_people():
                    report.bother_people(self)
                elif report.is_time_to_end():
                    self.single_report_responses(channel, report)


    def add_report(self, report):
        if report.channel not in self.reports:
            self.reports[report.channel] = {}
        self.reports[report.channel][report.name] = report

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
                    func = self.known_functions()[function_name]

                    try:
                        evaled = func(arg_to_function)
                        args.append((evaled, func.__annotations__.get('return', None)))
                    except Exception as e:
                        errors.append((function_name, e))

        return {
            'action': self.known_functions()[first_function_name],
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
            if word in self.known_tokens():
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

    def now_statement(self, text: str) -> datetime.datetime:
        """ enter how much time to wait in the format HH:MM """
        return datetime.datetime.utcnow()

    def num_statement(self, text: str) -> int:
        """ return a number value """
        try:
            return int(text)
        except:
            return 0

    def last_command_statement(self, channel: str) -> None:
        """ run the last command again """

        stuff = self.command_history.last_command(channel)
        action = stuff['action']
        args = stuff['args']

        action(*args)


    def known_tokens(self) -> List[str]:
        return list(self.known_functions().keys())

    def known_user_functions(self):
        return {
            'bother' : self.bother,
            'bother-all-now' : self.bother_all_now,
            'func-that-return' : self.functions_that_return,
            'error-help' : self.error_help,
            'help' : self.help,
            'responses' : self.responses,
            'list' : self.list,
            'reload-funcs' : self.reload_functions,
            'house-party' : self.party,
            'report-responses' : self.report_responses,
            'rollbar-item' : self.rollbar_item,
            'elm-progress' : self.elm_progress,
            'elm-progress-on' : self.elm_progress_on
        }

    def known_statements(self):
        return {
            'FOR' : self.for_statement,
            'AT' : self.at_statement,
            'WAIT' : self.wait_statement,
            'NOW' : self.now_statement,
            'NUM' : self.num_statement,
            '!!' : self.last_command_statement
        }

    def known_functions(self):
        return {**self.known_user_functions(), **self.known_statements()}

    def reload_functions(self, channel: str) -> None:
        """ reload the functions a bot knows """

        import importlib
        bot_file = importlib.import_module('bot_file')
        self.__class__ = bot_file.TodayIDidBot
        self.known_statements = types.MethodType(bot_file.TodayIDidBot.known_statements, self)
        self.known_user_functions = types.MethodType(bot_file.TodayIDidBot.known_user_functions, self)
        #TodayIDidBot.known_user_functions.fset(self, TodayIDidBot.known_user_functions.fget(self))
        #TodayIDidBot.known_statements.fset(self, TodayIDidBot.known_statements.fget(self))

    def party(self, channel: str) -> None:
        """ TADA """
        self.send_channel_message(channel, ':tada:')

    def elm_progress(self, channel: str, version: str) -> None:
        """ give a version of elm to get me to tell you how many number files are on master """

        version = version.strip()
        self.repo.get_ready()
        message = ""

        if version == '0.17':
            message += f"There are {self.repo.number_of_016_files}"
        elif version == '0.16':
            message += f"There are {self.repo.number_of_017_files}"
        else:
            num_016 = self.repo.number_of_016_files
            num_017 = self.repo.number_of_017_files
            message += f"There are {num_016} 0.16 files."
            message += f"\nThere are {num_017} 0.17 files."
            message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."

        self.send_channel_message(channel, message)

    def elm_progress_on(self, channel: str, branch_name: str) -> None:
        """ give a version of elm to get me to tell you how many number files are on master """

        self.repo.get_ready(branch_name)
        message = ""

        num_016 = self.repo.number_of_016_files
        num_017 = self.repo.number_of_017_files
        message += f"There are {num_016} 0.16 files."
        message += f"\nThere are {num_017} 0.17 files."
        message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."

        self.send_channel_message(channel, message)


    def rollbar_item(self, channel: str, field: str, counter: int) -> None:
        """ takes a counter, gets the rollbar info for that counter """

        rollbar_info = self.rollbar.get_item_by_counter(counter)

        if field == '' or field == 'all':
            pretty = json.dumps(rollbar_info, indent=4)
        else:
            pretty = rollbar_info.get(field, f'Could not find the field {field}')

        self.send_channel_message(channel, f'{pretty}')


    def list(self, channel: str) -> None:
        """ list known statements and functions """

        message = 'Main functions:\n'
        message += '\n'.join( f'`{func}`'for func in self.known_user_functions())
        message += '\nStatements:\n'
        message += '\n'.join( f'`{func}`'for func in self.known_statements())

        self.send_channel_message(channel, message)


    def help(self, channel: str, func_name: str) -> None:
        """ given a func_name preceeded with `~`, I'll tell you about it
        """
        func_name = func_name.strip()[1:]
        func = self.known_functions()[func_name]
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
        for report in self.reports[channel].values():
            message += f'for the report: {report.name}'
            message += '\n\n'.join(f'User {user} responded with:\n{response}' for (user, response) in report.responses.items())

        self.send_channel_message(channel, message)

    def report_responses(self, channel: str, name: str) -> None:
        """ list the last report responses for the current channel """

        name = name.strip()

        if channel not in self.reports or name not in self.reports[channel]:
            self.send_channel_message(channel, f'No reports found for channel {channel}')
            return

        self.single_report_responses(channel, self.reports[channel][name])

    def single_report_responses(self, channel: str, report) -> None:
        """ Send info on a single response """
        message = '\n\n'.join(f'User {user} responded with:\n{response}' for (user, response) in report.responses.items())

        if message == '':
            message = f'Nobody replied to the report {report.name}'
        else:
            message = f'For the report: {report.name}\n' + message
        self.send_channel_message(channel, message)


    def bother(self, channel: str, name: str, users: List[str], at: datetime.datetime, wait: datetime.datetime) -> None:
        """ add a report for the given users at a given time,
            reporting back in the channel requested
        """
        time_to_run = (at.hour, at.minute)
        wait_for = (wait.hour, wait.minute)
        self.add_report(Report(channel, name, time_to_run, users, wait_for))

    def bother_all_now(self, channel: str) -> None:
        """ run all the reports for a channel
        """
        for report in self.reports.get(channel, {}).values():
            report.bother_people(self)

    def error_help(self, channel: str, problem: str) -> None:
        """ present an error help message """
        if problem == 'NO_TOKENS':
            self.send_channel_message(channel, 'I\'m sorry, I couldn\'t find any tokens. Try using `help` or `list`')
        else:
            self.send_channel_message(channel, f'Some problem: {problem}')

    def functions_that_return(self, channel:str, text: str) -> None:
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
        message +='\n```'

        self.send_channel_message(channel, message)




class Report(object):
    def __init__(self, channel, name:str, time_to_run: Tuple[int,int], people, wait: Tuple[int, int], time_run=None):
        self.name = name
        self.people_to_bother = people
        self.channel = channel
        self.responses = {}
        self.time_run = time_run
        self.wait_for = wait
        self.time_to_run = time_to_run
        self.is_ended = False
        self.last_day_run = None

    def bother_people(self, client):
        if not self.people_to_bother:
            return

        self.responses = {}
        self.time_run = datetime.datetime.utcnow()
        client.send_channel_message(self.channel, 'Starting my report!')

        for person in self.people_to_bother[:]:
            client.send_message(person, 'Sorry to bother you!')
            self.add_response(person, '')
            self.people_to_bother.remove(person)

    def is_time_to_bother_people(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now_string = time.strftime("%j:%Y %H:%M:", time.gmtime(current_time))

        hour_mins = time_now_string.split(' ')[1].split(':')
        (hours, minutes) = hour_mins[0], hour_mins[1]
        time_now = (int(hours), int(minutes))

        if time_now < self.time_to_run:
            return False

        if self.time_run is not None:
            day_year = time_now_string.split(' ')[0].split(':')
            (day_in_year, year) = day_year[0], day_year[1]
            (time_run_day_in_year, time_run_year) = self.time_run.strftime('%j:%Y').split(':')

            if int(year) ==  int(time_run_year) and int(day_in_year) == int(time_run_day_in_year):
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
        self.save_responses()

    def save_responses(self):
        with open(f'reports/report-{self.name}-{self.channel}-{self.time_run}.json', 'w') as f:
            json.dump(self.responses, f)

    def save(self):
        with open(f'reports/report-config-{self.name}-{self.channel}.json', 'w') as f:
            json.dump(f, self.as_dict())

    def as_dict(self):
        return {
            'name' : self.name,
            'channel' : self.channel,
            'responses' : self.responses,
            'people_to_bother' : self.people_to_bother,
            'time_run' : (str(self.time_run) if self.time_run is not None else "")
        }

