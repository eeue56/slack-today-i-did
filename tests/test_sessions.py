import pytest
import os
import slack_today_i_did.reports as reports

MOCK_PERSON = 'dave'
MOCK_CHANNEL = '#durp'
MOCK_TEXT = 'abcdflk'
MOCK_TEST_FILE = '.testdata_sessions'


def test_start_session():
    sessions = reports.Sessions()

    sessions.start_session(MOCK_PERSON, MOCK_CHANNEL)

    assert MOCK_PERSON in sessions.sessions
    assert sessions.has_running_session(MOCK_PERSON)
    assert sessions.get_entry(MOCK_PERSON).get('channel') == MOCK_CHANNEL
    assert len(sessions.get_entry(MOCK_PERSON).get('messages')) == 0

    sessions.add_message(MOCK_PERSON, MOCK_TEXT)
    assert sessions.get_entry(MOCK_PERSON).get('channel') == MOCK_CHANNEL
    assert len(sessions.get_entry(MOCK_PERSON).get('messages')) == 1
    assert sessions.get_entry(MOCK_PERSON).get('messages') == [MOCK_TEXT]

def test_end_session():
    sessions = reports.Sessions()

    sessions.start_session(MOCK_PERSON, MOCK_CHANNEL)
    sessions.add_message(MOCK_PERSON, MOCK_TEXT)
    sessions.end_session(MOCK_PERSON)

    assert sessions.get_entry(MOCK_PERSON).get('channel') == MOCK_CHANNEL
    assert len(sessions.get_entry(MOCK_PERSON).get('messages')) == 1
    assert sessions.get_entry(MOCK_PERSON).get('messages') == [MOCK_TEXT]
    assert not sessions.has_running_session(MOCK_PERSON)


def test_session_saving_and_loading(tmpdir):
    sessions = reports.Sessions()
    sessions.load_from_file(MOCK_TEST_FILE)
    assert len(sessions.sessions) == 0

    sessions.start_session(MOCK_PERSON, MOCK_CHANNEL)
    sessions.add_message(MOCK_PERSON, MOCK_TEXT)
    sessions.save_to_file(MOCK_TEST_FILE)

    new_sessions = reports.Sessions()
    new_sessions.load_from_file(MOCK_TEST_FILE)
    assert len(new_sessions.sessions) == 1
    assert sessions.sessions == new_sessions.sessions

    os.remove(MOCK_TEST_FILE)


def test_session_retiring():
    sessions = reports.Sessions()
    sessions.start_session(MOCK_PERSON, MOCK_CHANNEL)
    sessions.add_message(MOCK_PERSON, MOCK_TEXT)
    sessions.retire_session(MOCK_PERSON, MOCK_TEST_FILE)
    assert len(sessions.sessions) == 0

    with open(MOCK_TEST_FILE) as f:
        assert MOCK_TEXT in f.read()

    os.remove(MOCK_TEST_FILE)
