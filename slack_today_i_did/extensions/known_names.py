import datetime
from typing import List
import json
import re
from collections import defaultdict
import importlib
import types

from slack_today_i_did.reports import Report
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.reports import Sessions
from slack_today_i_did.known_names import KnownNames
from slack_today_i_did.notify import Notification
import slack_today_i_did.parser as parser
import slack_today_i_did.text_tools as text_tools


class KnownNamesExtensions(BotExtension):
    def _setup_extension(self) -> None:
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


