import pytest

from slack_today_i_did.generic_bot import GenericSlackBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#general'


@pytest.fixture
def bot():
    return GenericSlackBot('')


def test_help_without_arg(mocker, bot, message_context):
    mocked_channel_message = mocker.patch.object(bot, 'send_channel_message')

    with message_context(bot, sender=MOCK_PERSON):
        bot.parse_direct_message({
            'user': MOCK_PERSON,
            'channel': MOCK_CHANNEL,
            'text': 'help'
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert "Main functions:" in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1


def test_help_on_func(mocker, bot, message_context):
    mocked_channel_message = mocker.patch.object(bot, 'send_channel_message')

    with message_context(bot, sender=MOCK_PERSON):
        bot.parse_direct_message({
            'user': MOCK_PERSON,
            'channel': MOCK_CHANNEL,
            'text': 'help help'
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert "I'll tell you about it" in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1


def test_help_on_mispelled_func(mocker, bot, message_context):
    mocked_channel_message = mocker.patch.object(bot, 'send_channel_message')

    with message_context(bot, sender=MOCK_PERSON):
        bot.parse_direct_message({
            'user': MOCK_PERSON,
            'channel': MOCK_CHANNEL,
            'text': 'help helc'
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert "I did find the following functions" in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1


def test_help_on_mispelled_something(mocker, bot, message_context):
    mocked_channel_message = mocker.patch.object(bot, 'send_channel_message')

    with message_context(bot, sender=MOCK_PERSON):
        bot.parse_direct_message({
            'user': MOCK_PERSON,
            'channel': MOCK_CHANNEL,
            'text': 'help hdebf8u3ijr9jndsiix'
        })

    assert MOCK_CHANNEL == mocked_channel_message.call_args[0][0]
    assert "I don't know what you mean and have no suggestions" in mocked_channel_message.call_args[0][1]
    assert mocked_channel_message.call_count == 1
