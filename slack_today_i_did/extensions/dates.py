import datetime
from typing import List
import json
import re
from collections import defaultdict
import importlib
import types
import random
import os

from slack_today_i_did.reports import Report
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.reports import Sessions
from slack_today_i_did.known_names import KnownNames
from slack_today_i_did.notify import Notification
import slack_today_i_did.parser as parser
import slack_today_i_did.text_tools as text_tools


HELP_TEXT = os.getenv('DATES_EXT_HELP', """
Hey everyone! These are your pairs for this week!
We suggest meeting at 13:00 on Wednesday, or find a date that works for you! 
    """.strip()).replace('\\n', '\n')

class DatesExtensions(BotExtension):
    def make_dates(self, channel: str) -> ChannelMessages:
        """ Grabs the known names to this bot! """
        channel_info = self.get_channel_info(channel)

        users = [user for user in channel_info['channel']['members'] if user != self.user_id]
        random.shuffle(users)

        extras = []

        if len(users) % 2 == 1:
            extras = users[-3:]
            users = users[:-3] 

        pairs = [f'[ <@{first}>, <@{second}> ]' for (first, second) in zip(users[::2], users[1::2])]

        if extras:
            extras_as_string = ', '.join(f"<@{x}>" for x in extras)
            pairs.append(f'[ {extras_as_string} ]')

        joined_pairs = '\n'.join(pairs)



        text_to_send = f"""
{HELP_TEXT}
{joined_pairs}
                """.strip()

        return ChannelMessage(channel, text_to_send)


