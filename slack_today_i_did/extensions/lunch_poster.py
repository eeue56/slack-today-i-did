import os
import json

from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from apiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

GOOGLE_SPREADSHEET_KEY = os.getenv('GOOGLE_SPREADSHEET_KEY', None)
SPREADSHEET_TO_OPEN = os.getenv('SPREADSHEET_TO_OPEN', '')


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
        self._google_spreadsheet_credentials = service_account.Credentials.from_service_account_info(spreadsheet_credentials, scopes=scopes)

    def display_lunch(self, channel: str) -> ChannelMessages:
        """ Shows the lunch options for the week """
        if self._google_spreadsheet_credentials is None:
            return []


        spreadsheet_service = build('sheets', 'v4', credentials=self._google_spreadsheet_credentials)


        results = spreadsheet_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_TO_OPEN, range='Sheet1!B1:F10', majorDimension="COLUMNS").execute()
        
        output = []
        for day in results['values']:
            bold_day = day.pop(0)

            output.append(f'*{bold_day}*\n' + '\n'.join(day))

        return ChannelMessage(channel, '\n\n'.join(output))
