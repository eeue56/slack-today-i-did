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
