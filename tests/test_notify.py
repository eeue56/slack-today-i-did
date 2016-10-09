import pytest
import os
import slack_today_i_did.notify as notify

MOCK_PERSON = 'dave'
MOCK_VALID_PATTERN = '[a]'
MOCK_INVALID_PATTERN = '['
MOCK_TEXT_WITH_PATTERN = 'a'
MOCK_TEXT_WITHOUT_PATTERN = "b"
MOCK_TEST_FILE = '.testdata_notify'


def test_add_pattern():
    notification = notify.Notification()

    notification.add_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)

    assert MOCK_PERSON in notification.patterns
    assert notification.patterns[MOCK_PERSON] == [MOCK_VALID_PATTERN]


def test_forget_pattern():
    notification = notify.Notification()

    notification.add_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)
    notification.forget_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)
    assert MOCK_PERSON in notification.patterns
    assert len(notification.patterns[MOCK_PERSON]) == 0


    notification.add_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)
    notification.forget_pattern(MOCK_PERSON, MOCK_INVALID_PATTERN)
    assert MOCK_PERSON in notification.patterns
    assert len(notification.patterns[MOCK_PERSON]) == 1


def test_who_wants_it():
    notification = notify.Notification()

    notification.add_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)

    who_wants_it = notification.who_wants_it(MOCK_TEXT_WITHOUT_PATTERN)
    assert len(who_wants_it) == 0

    who_wants_it = notification.who_wants_it(MOCK_TEXT_WITH_PATTERN)
    assert len(who_wants_it) == 1
    assert who_wants_it[0] == MOCK_PERSON


def test_saving_and_loading(tmpdir):


    notification = notify.Notification()
    notification.load_from_file(MOCK_TEST_FILE)
    assert len(notification.patterns) == 0

    notification.add_pattern(MOCK_PERSON, MOCK_VALID_PATTERN)
    notification.save_to_file(MOCK_TEST_FILE)

    assert len(notification.patterns) == 1

    new_notification = notify.Notification()
    new_notification.load_from_file(MOCK_TEST_FILE)
    assert len(new_notification.patterns) == 1
    assert notification.patterns == new_notification.patterns

    os.remove(MOCK_TEST_FILE)
