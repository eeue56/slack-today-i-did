import pytest
from typing import Union
import os
import slack_today_i_did.command_history as command_history

MOCK_CHANNEL = 'dave'
MOCK_FUNCTION_NAME = 'MOCK_FUNCTION'
MOCK_TEST_FILE = '.testdata_command_history'


def MOCK_FUNCTION():
    pass


MOCK_KNOWN_TOKENS = {
    'MOCK_FUNCTION': MOCK_FUNCTION
}
MOCK_UNION = Union[int, str]
MOCK_KNOWN_TYPES = (MOCK_UNION,)


def test_add_pattern():
    commands = command_history.CommandHistory()

    assert commands.last_command(MOCK_CHANNEL) is None

    commands.add_command(MOCK_CHANNEL, MOCK_FUNCTION, [])

    last_command = commands.last_command(MOCK_CHANNEL)

    assert last_command['action'] == MOCK_FUNCTION
    assert last_command['args'] == []
    assert commands.needs_save == True

    assert len(commands.history) == 1
    assert len(commands.history[MOCK_CHANNEL]) == 1


def test_saving_and_loading(tmpdir):
    history_file = str(tmpdir.join(MOCK_TEST_FILE))
    commands = command_history.CommandHistory()
    commands.load_from_file(MOCK_KNOWN_TOKENS, MOCK_KNOWN_TYPES, history_file)
    assert commands.last_command(MOCK_CHANNEL) is None
    assert commands.needs_save == False

    commands.add_command(MOCK_CHANNEL, MOCK_FUNCTION, [MOCK_UNION])
    commands.save_to_file(history_file)

    assert commands.last_command(MOCK_CHANNEL) is not None

    new_commands = command_history.CommandHistory()
    new_commands.load_from_file(MOCK_KNOWN_TOKENS, MOCK_KNOWN_TYPES, history_file)

    assert new_commands.last_command(MOCK_CHANNEL) is not None
    assert commands == new_commands
