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

    def needs_response(self, line: str) -> bool:
        return self.pattern.match(line)

    def respond(self, lines: str) -> str:
        pass

class QuipConfig(Config):
    def __init__(self, pattern: str, thread_id: str, quip: QuipExtensions):
        Config.__init__(self, pattern)
        self.thread_id = thread_id
        self._thread_message = quip._fetch_quip_doc(thread_id) if quip else None

    def respond(self, lines: str) -> str:
        if self._thread_message is None:
            return 

        return html2text.html2text(self._thread_message.get('html', ''))


class HardcodedConfig(Config):
    def __init__(self, pattern: str, message: str):
        Config.__init__(self, pattern)
        self.message = message

    def respond(self, lines: str) -> str:
        return self.message


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
