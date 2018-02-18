from typing import List
import types
import os
import json
import re
import html2text

from slack_today_i_did.reports import Report
import slack_today_i_did.external.quip as quip
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.extensions.quip import QuipExtensions

_config = os.getenv('BUG_REPORT_CONFIG', None)
BUG_REPORT_CONFIG = None if _config is None else json.loads(_config)

class Config(object):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)
        self.is_enabled = True

    def needs_response(self, line: str) -> bool:
        if not self.is_enabled: 
            return False
        return self.pattern.match(line)

    def respond(self, lines: str) -> str:
        pass

    def reload_response(self) -> None:
        return 

    def __str__(self):
        disabled_status = 'Enabled' if self.is_enabled else 'Disabled'
        return f'{disabled_status}. Watching for {self.pattern}.'


class QuipConfig(Config):
    def __init__(self, pattern: str, thread_id: str, quip: QuipExtensions):
        Config.__init__(self, pattern)
        self.thread_id = thread_id
        self.quip = quip
        self._thread_message = quip._fetch_quip_doc(thread_id) if quip else None

    def respond(self, lines: str) -> str:
        if self._thread_message is None:
            return 

        return html2text.html2text(self._thread_message.get('html', ''))

    def reload_response(self) -> None:
        self._thread_message = self.quip._fetch_quip_doc(self.thread_id) if self.quip else self._thread_message

    def __str__(self):
        parent_str = Config.__str__(self)

        return f'{parent_str} Quip doc: {self.thread_id}.' 


class HardcodedConfig(Config):
    def __init__(self, pattern: str, message: str):
        Config.__init__(self, pattern)
        self.message = message

    def respond(self, lines: str) -> str:
        return self.message

    def __str__(self):
        parent_str = Config.__str__(self)

        return f'{parent_str} Message: {self.message}.' 


class BugReportHintExtensions(QuipExtensions):
    """
        A bug report config looks like:

        [ { "channel": "help", "pattern": "Can anyone help me?", "source": "quip", "id": "2345678" } 
        , { "channel": "beginners", "pattern": "help?", "source": "hardcoded", "message": "Do you need help?"}]
    """

    def _setup_extension(self) -> None:
        if BUG_REPORT_CONFIG is None: 
            return 
        QuipExtensions._setup_extension(self)

        self._bug_messages = {}

        for config in BUG_REPORT_CONFIG:
            config_object = self.construct_config_object(config)
            if config_object is not None:
                self._bug_messages[config['channel']] = config_object

    def construct_config_object(self, config: any) -> Config:
        if config['source'] == 'quip':
            return QuipConfig(config['pattern'], config['id'], self)
        elif config['source'] == 'hardcoded':
            return HardcodedConfig(config['pattern'], config['message'])
        return None

    def _parse_message(self, channel, strings: List[str]) -> None:
        if BUG_REPORT_CONFIG is None: 
            return 

        channel_name = self.get_channel_info(channel).get('channel').get('name')
        config = self._bug_messages.get(channel_name, None)

        if config is None: 
            return 

        lines = '\n'.join(strings)
        if config.needs_response(lines):
            response = config.respond(lines)
            self.send_threaded_message(channel, self._last_message['ts'], response)


    def enable_bug_report_matcher(self, channel: str, channel_to_enable: str) -> ChannelMessages:
        """ Enable a bug report matcher for a given channel """
        if channel_to_enable not in self._bug_messages:
            return []

        self._bug_messages[channel_to_enable].is_enabled = True

        response = f'Enabled bug report helper for {channel_to_enable}'
        self.send_threaded_message(channel, self._last_message['ts'], response)

        return []


    def disable_bug_report_matcher(self, channel: str, channel_to_disable: str) -> ChannelMessages:
        """ Disable a bug report matcher for a given channel """
        if channel_to_disable not in self._bug_messages:
            return []

        self._bug_messages[channel_to_disable].is_enabled = False

        response = f'Disabled bug report helper for {channel_to_disable}'
        self.send_threaded_message(channel, self._last_message['ts'], response)

        return []


    def display_bug_report_config(self, channel: str, channel_info: str = None) -> ChannelMessages:
        """ Display config for a channel. If no channel provided, show for all channels """
        if channel_info is None:
            response = '\n'.join(f'Channel {channel_} : {config}' for (channel_, config) in self._bug_messages.items())
        elif channel_info in self._bug_messages:
            response = str(self._bug_messages[channel_info])
        else:
            response = f'No config for the channel {channel_info}'

        self.send_threaded_message(channel, self._last_message['ts'], response)

        return []

    def reload_bug_report_responses(self, channel: str, channel_info: str = None) -> ChannelMessages:
        """ Reload responses for a channel. If no channel provided, reload for all channels """
        if channel_info is None:
            for (channel, config) in self._bug_messages.items():
                config.reload_response() 
            response = "Reloaded all configs.."
        elif channel_info in self._bug_messages:
            self._bug_messages[channel_info].reload_response()
            response = "Reloaded config"
        else:
            response = f'No config for the channel {channel_info}'

        self.send_threaded_message(channel, self._last_message['ts'], response)

        return []
