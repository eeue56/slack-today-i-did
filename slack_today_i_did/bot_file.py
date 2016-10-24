"""
This file contains the bot itself

To add a new function:
    - add an entry in `known_functions`.
        The key is the command the bot will know, the value is the command to run
    - You must add type annotitions for the bot to match args up correctly

"""

from typing import Dict, Any

from slack_today_i_did.rollbar import Rollbar

from slack_today_i_did.extensions import (
    BasicStatements, KnownNamesExtensions,
    NotifyExtensions, ReportExtensions,
    SessionExtensions, RollbarExtensions,
    ElmExtensions, DeployComplexityExtensions
)

from slack_today_i_did.generic_bot import GenericSlackBot
import slack_today_i_did.self_aware as self_aware


class Extensions(
    BasicStatements, KnownNamesExtensions,
    NotifyExtensions, ReportExtensions,
    SessionExtensions, RollbarExtensions,
    ElmExtensions, DeployComplexityExtensions
):
    pass


class TodayIDidBot(Extensions, GenericSlackBot):

    def __init__(self, *args, **kwargs):
        kwargs = self._setup_from_kwargs_and_remove_fields(**kwargs)

        GenericSlackBot.__init__(self, *args, **kwargs)
        self.reports = {}
        self.name = 'today-i-did'

        self._setup_known_names()
        self._setup_notify()
        self._setup_sessions()
        self._setup_command_history()
        self._setup_deploy_complexity()

    def _setup_from_kwargs_and_remove_fields(self, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        rollbar_token = kwargs.pop('rollbar_token', None)
        if rollbar_token is None:
            self.rollbar = None
        else:
            self.rollbar = Rollbar(rollbar_token)

        self.repo = kwargs.pop('elm_repo', None)
        self.known_names_file = kwargs.pop('known_names_file', 'names.json')
        self.notify_file = kwargs.pop('notify_file', 'notify.json')
        self.session_file = kwargs.pop('session_file', 'sessions.json')
        self.command_history_file = kwargs.pop('command_history_file', 'command_history.json')
        return kwargs

    def _setup_command_history(self) -> None:
        known_functions = {action.__name__: action for action in self.known_functions().values()}
        self.command_history.load_from_file(known_functions, self.command_history_file)

    @property
    def features_enabled(self):
        return {
            "repo": self.repo is not None,
            "rollbar": self.rollbar is not None
        }

    def _actually_parse_message(self, message):
        GenericSlackBot._actually_parse_message(self, message)

        strings = []
        for attachment in message.get('attachments', []):
            strings.extend(self.attachment_strings(attachment))

        if 'text' in message:
            strings.append(message['text'])

        people_who_want_notification = []

        for string in strings:
            people_who_want_notification.extend(self.notify.who_wants_it(string))

        people_who_want_notification = set(people_who_want_notification)

        for person in people_who_want_notification:
            self.ping_person(message['channel'], person)

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

            'rollbar-item': self.rollbar_item,

            'elm-progress': self.elm_progress,
            'elm-progress-on': self.elm_progress_on,
            'find-017-matches': self.find_elm_017_matches,
            'how-hard-to-port': self.how_hard_to_port,

            'who-do-you-know': self.get_known_names,
            'know-me': self.add_known_name,

            'when-you-hear': self.when_you_hear,
            'forget': self.stop_listening,

            'start-session': self.start_session,
            'end-session': self.end_session,

            'deployed': self.last_prs
        }

    def reload_branch(self, channel: str, branch: str = None) -> None:
        """ reload a branch and trigger a restart """

        if branch is None:
            branch = self_aware.git_current_version()
            if branch.startswith('HEAD DETACHED'):
                return

            branch = branch.lstrip('On branch')

        self_aware.git_checkout(branch)
        self_aware.restart_program()

    def status(self, channel: str, show_all: str = None) -> None:
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

        self.send_channel_message(channel, message)

    def party(self, channel: str) -> None:
        """ TADA """
        self.send_channel_message(channel, ':tada:')
