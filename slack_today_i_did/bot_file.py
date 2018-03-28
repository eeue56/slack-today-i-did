"""
This file contains the bot itself

To add a new function:
    - add an entry in `known_functions`.
        The key is the command the bot will know, the value is the command to run
    - You must add type annotitions for the bot to match args up correctly

"""

from typing import Dict, Any, List

from slack_today_i_did.external.rollbar import Rollbar

from slack_today_i_did.extensions import (
    BasicStatements, KnownNamesExtensions,
    LunchPosterExtensions,
    NotifyExtensions, ReportExtensions,
    SessionExtensions, ExtensionExtensions,
    DatesExtensions, BugReportHintExtensions
)

from slack_today_i_did.generic_bot import GenericSlackBot, ChannelMessage, ChannelMessages
import slack_today_i_did.self_aware as self_aware


class Extensions(
    BasicStatements, KnownNamesExtensions,
    NotifyExtensions, ReportExtensions,
    LunchPosterExtensions,
    SessionExtensions, ExtensionExtensions,
    DatesExtensions, BugReportHintExtensions
):
    pass


class TodayIDidBot(Extensions, GenericSlackBot):

    def __init__(self, *args, **kwargs):
        kwargs = self._setup_from_kwargs_and_remove_fields(**kwargs)
        name = kwargs.pop('bot_name', '')

        GenericSlackBot.__init__(self, *args, **kwargs)
        self.name = name

        self.reports = {}

        print('Connecting with the name', self.name)
        self._setup_command_history()
        self.setup_extensions()

    def setup_extensions(self):
        known_bases = list(set(self._flatten_bases(self.__class__)))

        for extension in known_bases:
            for (func_name, func) in extension.__dict__.items():
                if func_name == '_setup_extension':
                    func(self)

    def _setup_from_kwargs_and_remove_fields(self, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        rollbar_token = kwargs.pop('rollbar_token', None)
        if rollbar_token is None:
            self.rollbar = None
        else:
            self.rollbar = Rollbar(rollbar_token)

        self.repo = kwargs.pop('elm_repo', None)
        self.reports_dir = kwargs.pop('reports_dir', 'reports')
        self.known_names_file = kwargs.pop('known_names_file', 'names.json')
        self.notify_file = kwargs.pop('notify_file', 'notify.json')
        self.session_file = kwargs.pop('session_file', 'sessions.json')
        self.command_history_file = kwargs.pop('command_history_file', 'command_history.json')
        return kwargs

    def _setup_command_history(self) -> None:
        known_functions = {action.__name__: action for action in self.known_functions().values()}
        self.command_history.load_from_file(known_functions, (ChannelMessages,), self.command_history_file)

    @property
    def features_enabled(self):
        return {
            "repo": self.repo is not None,
            "rollbar": self.rollbar is not None
        }

    def extension_parse(self, channel: str, messages: List[str]):
        known_bases = list(set(self._flatten_bases(self.__class__)))

        for extension in known_bases:
            for (func_name, func) in extension.__dict__.items():
                if func_name == '_parse_message':
                    func(self, channel, messages)

    def _actually_parse_message(self, message):
        GenericSlackBot._actually_parse_message(self, message)

        strings = []
        for attachment in message.get('attachments', []):
            strings.extend(self.attachment_strings(attachment))

        if 'text' in message:
            strings.append(message['text'])

        self.extension_parse(message['channel'], strings)

        if self.command_history.needs_save:
            self.command_history.save_to_file(self.command_history_file)

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

        if self.sessions.has_running_session(user):
            self.sessions.add_message(user, text)
            self.sessions.save_to_file(self.session_file)

    def on_tick(self):
        for (channel, reports) in self.reports.items():
            for report in reports.values():
                if report.is_time_to_bother_people():
                    report.bother_people(self)
                elif report.is_time_to_end():
                    self.single_report_responses(channel, report)

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
            'report-responses': self.report_responses,
            'responses': self.responses,

            'func-that-return': self.functions_that_return,
            'error-help': self.error_help,
            'help': self.help,
            'list': self.list,

            'reload-funcs': self.reload_functions,
            'reload': self.reload_branch,
            'status': self.status,

            'house-party': self.party,

            'who-do-you-know': self.get_known_names,
            'know-me': self.add_known_name,

            'when-you-hear': self.when_you_hear,
            'forget': self.stop_listening,

            'start-session': self.start_session,
            'end-session': self.end_session,

            'tokens-status': self.tokens_status,
            'disable-token': self.disable_token,
            'enable-token': self.enable_token,

            'known-ext': self.known_extensions,
            'disable-ext': self.disable_extension,
            'enable-ext': self.enable_extension,
            'load-ext': self.load_extension,

            'make-dates': self.make_dates,

            'display-lunch': self.display_lunch,


            'enable-bug-report': self.enable_bug_report_matcher,
            'disable-bug-report': self.disable_bug_report_matcher,
            'display-bug-report': self.display_bug_report_config,
            'reload-bug-report': self.reload_bug_report_responses
        }

    def reload_branch(self, channel: str, branch: str = None) -> ChannelMessages:
        """ reload a branch and trigger a restart """

        if branch is None:
            branch = self_aware.git_current_version()
            if branch.startswith('HEAD DETACHED'):
                return []

            on_branch_message = 'On branch'

            if branch.startswith(on_branch_message):
                branch = branch[len(on_branch_message):]

        self_aware.git_checkout(branch)
        self_aware.restart_program()

        return []

    def status(self, channel: str, show_all: str = None) -> ChannelMessages:
        """ provides meta information about the bot """

        current_version = self_aware.git_current_version()

        message = f"I am running on {current_version}\n"

        if show_all is not None:
            message += '-------------\n'
            message += '\n'.join(
                f'{feature} is {"enabled" if is_enabled else "disabled"}'
                for (feature, is_enabled) in self.features_enabled.items()
            )
            message += '\n-------------\n'

            message += f'Python version: {self_aware.python_version()}\n'
            message += f'Ruby version: {self_aware.ruby_version()}\n'

        return ChannelMessage(channel, message)

    def party(self, channel: str) -> ChannelMessages:
        """ TADA """
        return ChannelMessage(channel, ':tada:')
