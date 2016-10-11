import pytest
import os
from slack_today_i_did.bot_file import TodayIDidBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_TEXT = 'abcdflk'
MOCK_TEST_FILE = '.testdata_sessions'


def test_session(mocker):
    mocked_channel_message = mocker.patch.object(TodayIDidBot, 'send_channel_message')
    mocked_start_session = mocker.spy(TodayIDidBot, 'start_session')
    mocker.patch.object(TodayIDidBot, 'user_name_from_id', return_value=MOCK_PERSON)

    bot = TodayIDidBot('', rollbar_token='', elm_repo=None)

    bot.parse_direct_message({
        'user': MOCK_PERSON,
        'channel': MOCK_CHANNEL,
        'text': MOCK_TEXT
        })

    assert mocked_start_session.call_count == 1
    assert mocked_channel_message.call_count == 1
