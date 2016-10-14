import pytest
import os
from slack_today_i_did.bot_file import TodayIDidBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_START_SESSION_TEXT = 'start-session'
MOCK_TEST_FILE = '.testdata_sessions'


def test_session(mocker):
    mocked_channel_message = mocker.patch.object(TodayIDidBot, 'send_channel_message')
    mocker.patch.object(TodayIDidBot, 'was_directed_at_me', return_value=True)
    mocker.patch.object(TodayIDidBot, 'user_name_from_id', return_value=MOCK_PERSON)
    mocker.patch.object(TodayIDidBot, 'connected_user', return_value='TodayIDidBot')

    bot = TodayIDidBot('', rollbar_token='', elm_repo=None)
    bot._last_sender = MOCK_PERSON

    bot.parse_direct_message({
        'user': MOCK_PERSON,
        'channel': MOCK_CHANNEL,
        'text': MOCK_START_SESSION_TEXT
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert 'Started a session for you' in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1
