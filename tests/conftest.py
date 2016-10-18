import contextlib

import pytest


@pytest.fixture
def message_context(mocker):
    '''Sets up the specified `bot`'s state as if it just received
    a message from `sender` and about to parse it.

        with message_context(bot, MOCK_PERSON):
             do_stuff_with_the_bot(bot)
    '''
    @contextlib.contextmanager
    def wrapper(bot, sender):
        bot_qualname = f'{bot.__class__.__module__}.{bot.__class__.__qualname__}'
        mocker.patch(
            f'{bot_qualname}._last_sender',
            new_callable=mocker.PropertyMock, return_value=sender)
        mocker.patch.object(
            bot, 'user_name_from_id',
            return_value=sender)
        mocker.patch.object(
            bot, 'connected_user',
            return_value=bot.__class__.__name__)
        mocker.patch.object(
            bot, 'was_directed_at_me',
            return_value=True)

        yield

        mocker.stopall()

    return wrapper
