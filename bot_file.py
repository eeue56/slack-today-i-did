"""
This file contains the bot itself

To add a new function:
    - add an entry in `known_functions`.
        The key is the command the bot will know, the value is the command to run
    - You must add type annotitions for the bot to match args up correctly

"""
import datetime
import json
import re

from typing import List

from rollbar import Rollbar
from reports import Report
from generic_bot import GenericSlackBot
from known_names import KnownNames
from notify import Notification

import self_aware


class TodayIDidBot(GenericSlackBot):
    def __init__(self, *args, **kwargs):
        rollbar_token = kwargs.pop('rollbar_token', None)
        if rollbar_token is None:
            self.rollbar = None
        else:
            self.rollbar = Rollbar(rollbar_token)

        self.repo = kwargs.pop('elm_repo', None)
        self.known_names_file = kwargs.pop('known_names_file', 'names.json')
        self.notify_file = kwargs.pop('notify_file', 'notify.json')

        GenericSlackBot.__init__(self, *args, **kwargs)
        self.reports = {}
        self._user_id = None
        self.name = 'today-i-did'

        self.known_names = KnownNames()
        self.known_names.load_from_file(self.known_names_file)
        self.notify = Notification()
        self.notify.load_from_file(self.notify_file)

    def _actually_parse_message(self, message):
        GenericSlackBot._actually_parse_message(self, message)

        people_who_want_notification = None
        try:
            people_who_want_notification = self.notify.who_wants_it(message['text'])
        except Exception as e:
            pass

        if people_who_want_notification is not None:
            for person in people_who_want_notification:
                self.ping_person(message['channel'], person)

    def parse_direct_message(self, message):

        user = message['user']
        text = message['text']

        if self.was_directed_at_me(text):
            return self._actually_parse_message(message)

        name = self.user_name_from_id(user)

        for (channel_name, reports) in self.reports.items():
            for report in reports.values():
                if report.is_for_user(name):
                    report.add_response(name, text)
                    self.send_message(name, 'Thanks!')

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
        """ return the current time """
        return datetime.datetime.utcnow()

    def num_statement(self, text: str) -> int:
        """ return a number value """
        try:
            return int(text)
        except:
            return 0

    def known_statements(self):
        return {
            'FOR': self.for_statement,
            'AT': self.at_statement,
            'WAIT': self.wait_statement,
            'NOW': self.now_statement,
            'NUM': self.num_statement,
            '!!': self.last_command_statement
        }

    def known_user_functions(self):
        return {
            'bother': self.bother,
            'bother-all-now': self.bother_all_now,
            'func-that-return': self.functions_that_return,
            'error-help': self.error_help,
            'help': self.help,
            'responses': self.responses,
            'list': self.list,
            'reload-funcs': self.reload_functions,
            'reload': self.reload_branch,
            'house-party': self.party,
            'report-responses': self.report_responses,
            'rollbar-item': self.rollbar_item,
            'elm-progress': self.elm_progress,
            'elm-progress-on': self.elm_progress_on,
            'find-017-matches': self.find_elm_017_matches,
            'how-hard-to-port': self.how_hard_to_port,

            'who-do-you-know': self.get_known_names,
            'know-me': self.add_known_name,

            'when-you-hear': self.when_you_hear,
            'forget': self.stop_listening
        }

    def get_known_names(self, channel: str) -> None:
        """ Grabs the known names to this bot! """
        message = []

        for (person, names) in self.known_names.people.items():
            message.append(f'<@{person}> goes by the names {" | ".join(names)}')

        if len(message) == '':
            message = "I don't know nuffin or no one"

        self.send_channel_message(channel, '\n'.join(message))

    def add_known_name(self, channel: str, name: str) -> None:
        """ adds a known name to the collection for the current_user """
        person = self._last_sender

        self.known_names.add_name(person, name)
        self.known_names.save_to_file(self.known_names_file)

    def when_you_hear(self, channel: str, pattern: str) -> None:
        """ notify the user when you see a pattern """
        person = self._last_sender

        try:
            re.compile(pattern)
        except Exception as e:
            self.send_channel_message(channel, f'Invalid regex due to {e.msg}')
            return

        self.notify.add_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)
        self.send_channel_message(
            channel,
            f'Thanks! You be notified when I hear that pattern. Use `forget` to stop me notifying you!'
        )

    def stop_listening(self, channel: str, pattern: str) -> None:
        """ stop notify the user when you see a pattern """
        person = self._last_sender

        self.notify.forget_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)

    def ping_person(self, channel: str, person: str) -> None:
        """ notify a person about a message. Ignore direct messages """
        if self.is_direct_message(channel):
            return

        self.send_channel_message(channel, f"<@{person}> ^")

    def reload_branch(self, channel: str, branch: str) -> None:
        """ reload a branch and trigger a restart """
        self_aware.git_checkout(branch)

        self_aware.restart_program()

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
        message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."  # noqa: E501

        self.send_channel_message(channel, message)

    def find_elm_017_matches(self, channel: str, filename_pattern: str) -> None:  # noqa: E501
        """ give a filename of elm to get me to tell you how it looks on master """  # noqa: E501

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        filenames = self.repo.get_files_for_017(filename_pattern)
        message += " | ".join(filenames)

        self.send_channel_message(channel, message)

    def how_hard_to_port(self, channel: str, filename_pattern: str) -> None:
        """ give a filename of elm to get me to tell you how hard it is to port
            Things are hard if: contains ports, signals, native or html.
            Ports and signals are hardest, then native, then html.
        """

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        files = self.repo.get_017_porting_breakdown(filename_pattern)

        message += f'Here\'s the breakdown for the:'

        for (filename, breakdown) in files.items():
            total_hardness = sum(breakdown.values())
            message += f'\nfile {filename}: total hardness {total_hardness}\n'
            message += ' | '.join(
                f'{name} : {value}' for (name, value) in breakdown.items()
            )

        self.send_channel_message(channel, message)

    def rollbar_item(self, channel: str, field: str, counter: int) -> None:
        """ takes a counter, gets the rollbar info for that counter """

        rollbar_info = self.rollbar.get_item_by_counter(counter)

        if field == '' or field == 'all':
            pretty = json.dumps(rollbar_info, indent=4)
        else:
            pretty = rollbar_info.get(
                field,
                f'Could not find the field {field}'
            )

        self.send_channel_message(channel, f'{pretty}')

    def responses(self, channel: str) -> None:
        """ list the last report responses for the current channel """

        if channel not in self.reports:
            self.send_channel_message(
                channel,
                f'No reports found for channel {channel}'
            )
            return

        message = ""
        for report in self.reports[channel].values():
            message += f'for the report: {report.name}'
            message += '\n\n'.join(
                f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
            )

        self.send_channel_message(channel, message)

    def report_responses(self, channel: str, name: str) -> None:
        """ list the last report responses for the current channel """

        name = name.strip()

        if channel not in self.reports or name not in self.reports[channel]:
            self.send_channel_message(
                channel,
                f'No reports found for channel {channel}'
            )

            return

        self.single_report_responses(channel, self.reports[channel][name])

    def single_report_responses(self, channel: str, report) -> None:
        """ Send info on a single response """
        message = '\n\n'.join(
            f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
        )

        if message == '':
            message = f'Nobody replied to the report {report.name}'
        else:
            message = f'For the report: {report.name}\n' + message
        self.send_channel_message(channel, message)

    def bother(self, channel: str, name: str, users: List[str], at: datetime.datetime, wait: datetime.datetime) -> None:  # noqa: E501
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
