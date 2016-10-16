import pytest
import os
from slack_today_i_did.bot_file import TodayIDidBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_START_SESSION_TEXT = 'start-session'
MOCK_TEST_FILE = '.testdata_sessions'


@pytest.fixture
def bot_with_message(mocker):
    bot = TodayIDidBot('', rollbar_token='', elm_repo=None)
    bot._last_sender = MOCK_PERSON
    mocker.patch.object(bot, 'user_name_from_id', return_value=MOCK_PERSON)
    mocker.patch.object(bot, 'connected_user', return_value='TodayIDidBot')
    mocker.patch.object(bot, 'was_directed_at_me', return_value=True)
    return bot


# TODO: this probably should be tested in a file named test_generic_bot.py
def test_help(mocker, bot_with_message):
    mocked_channel_message = mocker.patch.object(
        bot_with_message, 'send_channel_message')

    bot_with_message.parse_direct_message({
        'user': MOCK_PERSON,
        'channel': MOCK_CHANNEL,
        'text': 'help help'
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert "I'll tell you about it" in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1


def test_start_session(mocker, bot_with_message):
    mocked_channel_message = mocker.patch.object(
        bot_with_message, 'send_channel_message')

    bot_with_message.parse_direct_message({
        'user': MOCK_PERSON,
        'channel': MOCK_CHANNEL,
        'text': MOCK_START_SESSION_TEXT
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert 'Started a session for you' in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1
