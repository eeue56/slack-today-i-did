import datetime
from typing import List
import json
import re
import subprocess
from collections import defaultdict
import importlib
import types

from slack_today_i_did.reports import Report
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.reports import Sessions
from slack_today_i_did.known_names import KnownNames
from slack_today_i_did.notify import Notification
from slack_today_i_did.our_repo import OurRepo
import slack_today_i_did.parser as parser
import slack_today_i_did.text_tools as text_tools


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

    def now_statement(self) -> datetime.datetime:
        """ return the current time """
        return datetime.datetime.utcnow()

    def num_statement(self, text: str) -> int:
        """ return a number value """
        try:
            return int(text)
        except:
            return 0


class ExtensionExtensions(BotExtension):
    def _setup_enabled_tokens(self):
        """ Store disabled tokens in a dict of token: user
            Store disabled extensions in just a list of class names
        """
        self._disabled_tokens = {}
        self._disabled_extensions = []

    def _disabled_message(self, who: str, channel: str) -> ChannelMessages:
        # TODO: this function is currently evaluated in the wrong way by the evaluator
        # so we send the message by hand
        self.send_channel_message(channel, f'This function has been disabled by {who}.')
        return []

    def _flatten_bases(self, cls):
        """ Get all the extensions applied to a bot instance
        """
        bases = cls.__bases__
        known_bases = []

        for base in bases:
            if base.__name__ == 'object':
                continue

            current_bases = self._flatten_bases(base)

            known_bases.append(base)

            if BotExtension in current_bases:
                known_bases.extend(current_bases)

        return known_bases

    def known_functions(self):
        known_functions = BotExtension.known_functions(self)

        try:
            if len(self._disabled_tokens) == 0:
                return known_functions
        except:
            return known_functions

        wrapped_functions = {
            k: v for (k, v) in known_functions.items()
            if k not in self._disabled_tokens
        }

        wrapped_functions.update({
            token: lambda *args, **kwargs: self._disabled_message(who, *args, **kwargs)
            for (token, who) in self._disabled_tokens.items()
        })

        return wrapped_functions

    def known_extensions(self, channel: str) -> ChannelMessages:
        """ List all extensions used by the current bot """
        known_bases = list(set(self._flatten_bases(self.__class__)))

        message = 'Currently known extensions:\n'
        message += '\n'.join(base.__name__ for base in known_bases)

        return ChannelMessage(channel, message)

    def tokens_status(self, channel: str) -> ChannelMessages:
        """ Display all the known tokens and if they are enabled """
        known_tokens = [
            (token, token not in self._disabled_tokens) for token in self.known_tokens()
        ]

        message = '\n'.join(f'{token}: {is_enabled}' for (token, is_enabled) in known_tokens)

        return ChannelMessage(channel, message)

    def _manage_extension(self, extension_name: str, is_to_enable: bool, disabler: str) -> None:
        """ Disable or enable an extension, setting who disabled it """
        known_bases = list(set(self._flatten_bases(self.__class__)))
        flipped_tokens = {
            func.__name__: func_alias for (func_alias, func) in self.known_functions().items()
        }

        extensions = [base for base in known_bases if base.__name__ == extension_name]

        for extension in extensions:
            for func in extension.__dict__:
                if func not in flipped_tokens:
                    continue

                if is_to_enable:
                    self._disabled_tokens.pop(flipped_tokens[func], None)
                else:
                    self._disabled_tokens[flipped_tokens[func]] = disabler

            if is_to_enable:
                self._disabled_extensions.remove(extension.__name__)
            else:
                self._disabled_extensions.append(extension.__name__)

    def enable_extension(self, channel: str, extension_name: str) -> ChannelMessages:
        """ enable an extension and all it's exposed tokens by name """
        self._manage_extension(extension_name, is_to_enable=True, disabler=self._last_sender)
        return []

    def disable_extension(self, channel: str, extension_name: str) -> ChannelMessages:
        """ disable an extension and all it's exposed tokens by name """
        self._manage_extension(extension_name, is_to_enable=False, disabler=self._last_sender)
        return []

    def load_extension(self, channel: str, extension_name: str = None) -> ChannelMessages:
        """ Load extensions. By default, load everything.
            Otherwise, load a particular extension
        """
        known_bases = list(set(self._flatten_bases(self.__class__)))
        known_bases_as_str = [base.__name__ for base in known_bases]
        func_names = [func.__name__ for func in self.known_functions().values()]
        meta_funcs = [
            func.__name__ for func in self.known_functions().values() if parser.is_metafunc(func)
        ]

        # make sure to pick up new changes
        importlib.invalidate_caches()

        # import and reload ourselves
        extensions = importlib.import_module(__name__)
        importlib.reload(extensions)

        extension_names = dir(extensions)
        if extension_name is not None and extension_name.strip() != "":
            if extension_name not in extension_names:
                suggestions = [
                    (text_tools.levenshtein(extension_name, name), name) for name in extension_names
                ]

                message = 'No such extension! Maybe you meant one of these:\n'
                message += ' | '.join(name for (_, name) in sorted(suggestions)[:5])
                return ChannelMessage(channel, message)
            else:
                extension_names = [extension_name]

        for extension in extension_names:
            # skip if the extension is not a superclass
            if extension not in known_bases_as_str:
                continue

            extension_class = getattr(extensions, extension)

            for (func_name, func) in extension_class.__dict__.items():
                # we only care about reloading things in our tokens
                if func_name not in func_names:
                    continue

                # ensure that meta_funcs remain so
                if func_name in meta_funcs:
                    func = parser.metafunc(func)

                setattr(self, func_name, types.MethodType(func, self))

        return []

    @parser.metafunc
    def enable_token(self, channel: str, tokens) -> ChannelMessages:
        """ enable tokens """
        for token in tokens:
            if token.func_name in self._disabled_tokens:
                self._disabled_tokens.pop(token.func_name, None)
        return []

    @parser.metafunc
    def disable_token(self, channel: str, tokens) -> ChannelMessages:
        """ disable tokens """
        for token in tokens:
            func_name = token.func_name
            self._disabled_tokens[func_name] = self._last_sender

        return []


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
        self.add_report(Report(channel, name, time_to_run, users, wait_for, reports_dir=self.reports_dir))
        return []

    def bother_all_now(self, channel: str) -> ChannelMessages:
        """ run all the reports for a channel
        """
        messages = []
        for report in self.reports.get(channel, {}).values():
            bothers = [ChannelMessage(*bother) for bother in report.bother_people()]
            messages.extend(bothers)
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

        with self.repo.cached_lookups():
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

        message += '\n---------------\n'
        message += 'For a total of:\n'
        message += ' | '.join(
            f'{name} : {value}' for (name, value) in total_breakdowns.items()
        )
        return ChannelMessage(channel, message)


class DeployComplexityExtensions(BotExtension):
    def _setup_deploy_complexity(self) -> None:
        self.deploy_complexity_repo = OurRepo('repos', "", "NoRedInk", "deploy-complexity")

    def last_prs(self, channel: str) -> ChannelMessages:
        """ list the PRs in the main repo """


        self.deploy_complexity_repo.get_ready()
        self.repo.get_ready()

        script_location = f'{self.deploy_complexity_repo.repo_dir}/deploy-complexity.rb'

        output = subprocess.check_output([
            script_location,
            "--git-dir",
            self.repo.repo_dir,
            "staging",
            "-d",
            "1",
            "--gh-url",
            f"https://github.com/{self.repo.org}/{self.repo.repo}"
        ])

        message = output.decode()

        return ChannelMessage(channel, message)
