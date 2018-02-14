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


