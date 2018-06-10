import os
import json
from datetime import datetime


from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from apiclient.discovery import build
from google.oauth2 import service_account

GOOGLE_SPREADSHEET_KEY = os.getenv('GOOGLE_SPREADSHEET_KEY', None)
SPREADSHEET_TO_OPEN = os.getenv('SPREADSHEET_TO_OPEN', '')


def current_day():
    days = ["Mandag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lordag", "Lisdag"]

    current_day_number = datetime.today().weekday()

    return days[current_day_number]


class LunchPosterExtensions(BotExtension):
    def _setup_extension(self):
        self._google_spreadsheet_credentials = None
        self._gspread = None

        if GOOGLE_SPREADSHEET_KEY is None:
            return

        spreadsheet_credentials = json.loads(GOOGLE_SPREADSHEET_KEY)

        scopes = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self._google_spreadsheet_credentials = service_account.Credentials.from_service_account_info(
            spreadsheet_credentials,
            scopes=scopes
        )

    def display_lunch(self, channel: str, day_name: str = None) -> ChannelMessages:
        """ Shows the lunch options for the week """
        if self._google_spreadsheet_credentials is None:
            return []

        spreadsheet_service = build('sheets', 'v4', credentials=self._google_spreadsheet_credentials)

        results = spreadsheet_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_TO_OPEN,
            range='Sheet1!B1:F10',
            majorDimension="COLUMNS"
        ).execute()

        messages = []

        if day_name is None:
            for day in results['values']:
                bold_day = day.pop(0)
                messages.append(ChannelMessage(channel, f'*{bold_day}*\n\n'))
                messages.extend([ChannelMessage(channel, menu) for menu in day])
        else:
            if day_name.strip().lower() == 'today':
                day_name = current_day()

            for day in results['values']:
                bold_day = day.pop(0)

                if bold_day.strip().lower() != day_name.strip().lower():
                    continue
                messages.append(ChannelMessage(channel, f'*{bold_day}*\n\n'))
                messages.extend([ChannelMessage(channel, menu) for menu in day])

        return messages
