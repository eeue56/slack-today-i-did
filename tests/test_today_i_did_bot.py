import pytest
import os
from slack_today_i_did.bot_file import TodayIDidBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_START_SESSION_TEXT = 'start-session'
MOCK_TEST_FILE = '.testdata_sessions'


@pytest.fixture
def bot():
    return TodayIDidBot('', rollbar_token='', elm_repo=None)


def test_start_session(mocker, bot, message_context):
    mocked_channel_message = mocker.patch.object(bot, 'send_channel_message')

    with message_context(bot, sender=MOCK_PERSON):
        bot.parse_direct_message({
            'user': MOCK_PERSON,
            'channel': MOCK_CHANNEL,
            'text': MOCK_START_SESSION_TEXT
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert 'Started a session for you' in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1
