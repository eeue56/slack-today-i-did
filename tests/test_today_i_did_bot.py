import pytest
import os
import inspect
import typing
import functools
import datetime
from slack_today_i_did import parser
from slack_today_i_did.bot_file import TodayIDidBot

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_START_SESSION_TEXT = 'start-session'
MOCK_TEST_FILE = '.testdata_sessions'
MOCK_COMMAND_HISTORY = '.testdata_test_today_i_did_bot_command_history'


@pytest.fixture
def bot(tmpdir):
    reports_dir = tmpdir.mkdir("reports")
    return TodayIDidBot(
        '',
        rollbar_token='',
        elm_repo=None,
        reports_dir=str(reports_dir),
        command_history_file=str(tmpdir.join('command_history.json')))


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


@pytest.mark.skip
def test_save_and_load_known_user_func_history(mocker, bot, message_context):
    dangerous_commands = ('reload', 'reload-funcs', 'status', 'make-dates')
    default_args = ('channel',)
    sample_args = {
        int: 'NUM 1',
        str: 'orange',
        datetime.datetime: 'NOW',
        typing.List[str]: 'FOR blurb,blabi',
        inspect._empty: 'help', # guessing it's help's `args` param
    }

    expected_func_names = []

    for command, func in bot.known_user_functions().items():
        if command in dangerous_commands:
            continue

        signature = inspect.signature(func)
        args = (sample_args[param.annotation]
                for (name, param) in signature.parameters.items()
                if name not in default_args)
        message_text = f'{command} {" ".join(args)}'.strip()

        with message_context(bot, sender=MOCK_PERSON):
            spy = mocker.spy(bot, func.__name__)
            mocker.patch.object(bot.rollbar, 'get_item_by_counter', return_value={})
            mocker.patch.object(bot, 'repo')

            # preserve important attributes on the spy
            functools.update_wrapper(spy, func)
            if parser.is_metafunc(func):
                parser.metafunc(spy)

            bot.parse_direct_message({
                'user': MOCK_PERSON,
                'channel': MOCK_CHANNEL,
                'text': message_text
            })

            assert spy.call_count == 1
            expected_func_names.append(func.__name__)

        second_bot = TodayIDidBot('', command_history_file=bot.command_history_file, reports_dir=bot.reports_dir)
        saved_func_names = [command['action'].__name__
                          for command in second_bot.command_history.history[MOCK_CHANNEL]]
        assert saved_func_names == expected_func_names
