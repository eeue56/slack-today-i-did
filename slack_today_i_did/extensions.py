import datetime
from typing import List
import json
import re
from collections import defaultdict

from slack_today_i_did.reports import Report
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.reports import Sessions
from slack_today_i_did.known_names import KnownNames
from slack_today_i_did.notify import Notification


class BasicStatements(BotExtension):
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


class KnownNamesExtensions(BotExtension):
    def _setup_known_names(self) -> None:
        self.known_names = KnownNames()
        self.known_names.load_from_file(self.known_names_file)

    def get_known_names(self, channel: str) -> ChannelMessages:
        """ Grabs the known names to this bot! """
        message = []

        for (person, names) in self.known_names.people.items():
            message.append(f'<@{person}> goes by the names {" | ".join(names)}')

        if len(message) == '':
            message = "I don't know nuffin or no one"

        return ChannelMessage(channel, '\n'.join(message))

    def add_known_name(self, channel: str, name: str) -> ChannelMessages:
        """ adds a known name to the collection for the current_user """
        person = self._last_sender

        self.known_names.add_name(person, name)
        self.known_names.save_to_file(self.known_names_file)

        return []


class NotifyExtensions(BotExtension):
    def _setup_notify(self) -> None:
        self.notify = Notification()
        self.notify.load_from_file(self.notify_file)

    def when_you_hear(self, channel: str, pattern: str) -> ChannelMessages:
        """ notify the user when you see a pattern """
        person = self._last_sender

        try:
            re.compile(pattern)
        except Exception as e:
            return ChannelMessage(channel, f'Invalid regex due to {e.msg}')

        self.notify.add_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)
        return ChannelMessage(
            channel,
            f'Thanks! You be notified when I hear that pattern. Use `forget` to stop me notifying you!'
        )

    def stop_listening(self, channel: str, pattern: str) -> ChannelMessages:
        """ stop notify the user when you see a pattern """
        person = self._last_sender

        self.notify.forget_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)

        return []

    def ping_person(self, channel: str, person: str) -> ChannelMessages:
        """ notify a person about a message. Ignore direct messages """
        if self.is_direct_message(channel):
            return

        return ChannelMessage(channel, f"<@{person}> ^")


class ReportExtensions(BotExtension):
    def responses(self, channel: str) -> ChannelMessages:
        """ list the last report responses for the current channel """

        if channel not in self.reports:
            return ChannelMessage(
                channel,
                f'No reports found for channel {channel}'
            )

        message = ""
        for report in self.reports[channel].values():
            message += f'for the report: {report.name}'
            message += '\n\n'.join(
                f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
            )

        return ChannelMessage(channel, message)

    def report_responses(self, channel: str, name: str) -> ChannelMessages:
        """ list the last report responses for the current channel """

        name = name.strip()

        if channel not in self.reports or name not in self.reports[channel]:
            return ChannelMessage(
                channel,
                f'No reports found for channel {channel}'
            )

        return self.single_report_responses(channel, self.reports[channel][name])

    def single_report_responses(self, channel: str, report) -> ChannelMessages:
        """ Send info on a single response """
        message = '\n\n'.join(
            f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
        )

        if message == '':
            message = f'Nobody replied to the report {report.name}'
        else:
            message = f'For the report: {report.name}\n' + message
        return ChannelMessage(channel, message)

    def bother(self, channel: str, name: str, users: List[str], at: datetime.datetime, wait: datetime.datetime) -> ChannelMessages:  # noqa: E501
        """ add a report for the given users at a given time,
            reporting back in the channel requested
        """
        time_to_run = (at.hour, at.minute)
        wait_for = (wait.hour, wait.minute)
        self.add_report(Report(channel, name, time_to_run, users, wait_for))
        return []

    def bother_all_now(self, channel: str) -> ChannelMessages:
        """ run all the reports for a channel
        """
        messages = []
        for report in self.reports.get(channel, {}).values():
            messages.extend(report.bother_people())
        return messages

    def add_report(self, report):
        if report.channel not in self.reports:
            self.reports[report.channel] = {}
        self.reports[report.channel][report.name] = report


class SessionExtensions(BotExtension):
    def _setup_sessions(self) -> None:
        self.sessions = Sessions()
        self.sessions.load_from_file(self.session_file)

    def start_session(self, channel: str) -> ChannelMessages:
        """ starts a session for a user """
        person = self._last_sender
        self.sessions.start_session(person, channel)
        self.sessions.save_to_file(self.session_file)

        message = """
Started a session for you. Send a DMs to me with what you're working on throughout the day.
Tell me `end-session` to finish the session and post it here!
"""
        return ChannelMessage(channel, message.strip())

    def end_session(self, channel: str) -> ChannelMessages:
        """ ends a session for a user """

        person = self._last_sender
        if not self.sessions.has_running_session(person):
            return ChannelMessage(channel, 'No session running.')

        self.sessions.end_session(person)
        self.sessions.save_to_file(self.session_file)

        entry = self.sessions.get_entry(person)

        message = f'Ended a session for the user <@{person}>. They said the following:\n'
        message += '\n'.join(entry['messages'])
        return ChannelMessage(entry['channel'], message)


class RollbarExtensions(BotExtension):
    def rollbar_item(self, channel: str, field: str, counter: int) -> ChannelMessages:
        """ takes a counter, gets the rollbar info for that counter """

        rollbar_info = self.rollbar.get_item_by_counter(counter)

        if field == '' or field == 'all':
            pretty = json.dumps(rollbar_info, indent=4)
        else:
            pretty = rollbar_info.get(
                field,
                f'Could not find the field {field}'
            )

        return ChannelMessage(channel, f'{pretty}')


class ElmExtensions(BotExtension):
    def elm_progress(self, channel: str, version: str) -> ChannelMessages:
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

        return ChannelMessage(channel, message)

    def elm_progress_on(self, channel: str, branch_name: str) -> ChannelMessages:
        """ give a version of elm to get me to tell you how many number files are on master """

        self.repo.get_ready(branch_name)
        message = ""

        num_016 = self.repo.number_of_016_files
        num_017 = self.repo.number_of_017_files
        message += f"There are {num_016} 0.16 files."
        message += f"\nThere are {num_017} 0.17 files."
        message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."  # noqa: E501

        return ChannelMessage(channel, message)

    def find_elm_017_matches(self, channel: str, filename_pattern: str) -> ChannelMessages:  # noqa: E501
        """ give a filename of elm to get me to tell you how it looks on master """  # noqa: E501

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        filenames = self.repo.get_files_for_017(filename_pattern)
        message += " | ".join(filenames)

        return ChannelMessage(channel, message)

    def how_hard_to_port(self, channel: str, filename_pattern: str) -> ChannelMessages:
        """ give a filename of elm to get me to tell you how hard it is to port
            Things are hard if: contains ports, signals, native or html.
            Ports and signals are hardest, then native, then html.
        """

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        with self.repo.lock():
            files = self.repo.get_017_porting_breakdown(filename_pattern)

        message += f'Here\'s the breakdown for the:'

        total_breakdowns = defaultdict(int)

        for (filename, breakdown) in files.items():
            total_hardness = sum(breakdown.values())
            message += f'\nfile {filename}: total hardness {total_hardness}\n'
            message += ' | '.join(
                f'{name} : {value}' for (name, value) in breakdown.items()
            )

            for (name, value) in breakdown.items():
                total_breakdowns[name] += value

        message += '---------------\n'
        message += 'For a total of:\n'
        message += ' | '.join(
            f'{name} : {value}' for (name, value) in total_breakdowns.items()
        )

        return ChannelMessage(channel, message)

