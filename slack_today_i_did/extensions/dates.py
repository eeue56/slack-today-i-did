import datetime
from typing import List
import json
import re
from collections import defaultdict
import importlib
import types
import random
import os

from datetime import datetime, timedelta

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


def get_next_day(dayname, start_date=None):
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    if start_date is None:
        start_date = datetime.today()
    day_num_target = weekdays.index(dayname)

    while start_date.weekday() != day_num_target:
        start_date += timedelta(days=1)

    return start_date

def get_user_email(user) -> str: 
    if user.get('user', False):
        if user['user'].get('profile', False):
            return user['user']['profile'].get('email', '')

    return ''

class DatesExtensions(BotExtension):
    def _create_calendar_event(self, users):
        from google.oauth2 import service_account
        from apiclient.discovery import build

        calendar_credentials = json.loads(os.getenv('GOOGLE_CALENDAR_KEY', ''))
        credentials = service_account.Credentials.from_service_account_info(calendar_credentials)

        calendar_service = build('calendar', 'v3', credentials=credentials)

        next_wednesday = get_next_day("Wednesday").replace(hour=13, minute=0, second=0)

        end = next_wednesday + timedelta(minutes=30)

        timestamp = next_wednesday.isoformat()
        end_timestamp = end.isoformat()

        user_info = [self.get_user_info(user) for user in users]
        user_emails = [ get_user_email(user) for user in user_info ]

        event = {
          'summary': 'Speed date',
          'location': '',
          'description': 'A chance to get to know each other better!',
          'start': {
            'dateTime': timestamp,
            'timeZone': 'Europe/Oslo',
          },
          'end': {
            'dateTime': end_timestamp,
            'timeZone': 'Europe/Oslo',
          },
          'recurrence': [
          ],
          'attendees': [
            { "email": email } for email in user_emails
          ],
          'reminders': {
            'useDefault': True
          },
          'guestsCanModify': True,
        }


        event = calendar_service.events().insert(calendarId='primary', body=event, sendNotifications=True).execute()


    def make_dates(self, channel: str) -> ChannelMessages:
        """ Create random dates based on the people in the channel """

        channel_info = self.get_channel_info(channel)

        users = [user for user in channel_info['channel']['members'] if user != self.user_id]
        random.shuffle(users)

        extras = []

        if len(users) % 2 == 1:
            extras = users[-3:]
            users = users[:-3] 

        user_pairs = zip(users[::2], users[1::2])

        pairs = [f'[ <@{first}>, <@{second}> ]' for (first, second) in user_pairs]

        if extras:
            extras_as_string = ', '.join(f"<@{x}>" for x in extras)
            pairs.append(f'[ {extras_as_string} ]')

        joined_pairs = '\n'.join(pairs)


        text_to_send = f"""
{HELP_TEXT}
{joined_pairs}
                """.strip()

        if os.getenv('GOOGLE_CALENDAR_KEY', None) is not None:
            for pair in user_pairs:
                self._create_calendar_event(pair)
            if extras: 
                self._create_calendar_event(extras)

        return ChannelMessage(channel, text_to_send)


