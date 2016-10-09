import pytest
import slack_today_i_did.parser as parser

MOCK_TOKENS = {
    'hello': lambda x:x,
    'NOW': lambda x:x
}

TEXT_WITHOUT_TOKENS = 'dave fish'
TEXT_WITH_TOKEN = "hello dave"
TEXT_WITH_TOKENS = "hello dave NOW"


def test_tokens_with_index_on_no_tokens():
    tokens = parser.tokens_with_index(MOCK_TOKENS, TEXT_WITHOUT_TOKENS)
    assert len(tokens) == 0


def test_tokens_with_index_on_single_token():
    tokens = parser.tokens_with_index(MOCK_TOKENS, TEXT_WITH_TOKEN)
    assert len(tokens) == 1

    first_token = tokens[0]

    assert first_token[0] == 0
    assert first_token[1] == 'hello'


def test_tokens_with_index_on_tokens():
    tokens = parser.tokens_with_index(MOCK_TOKENS, TEXT_WITH_TOKENS)
    assert len(tokens) == 2

    first_token = tokens[0]
    second_token = tokens[1]

    assert first_token[0] == 0
    assert first_token[1] == 'hello'
    assert second_token[0] == 11
    assert second_token[1] == 'NOW'


def test_tokenize_on_no_tokens():
    tokens = parser.tokenize(TEXT_WITHOUT_TOKENS, MOCK_TOKENS)
    assert len(tokens) == 0


def test_tokenize_on_one_token():
    tokens = parser.tokenize(TEXT_WITH_TOKEN, MOCK_TOKENS)
    assert len(tokens) == 1
    first_token = tokens[0]

    assert first_token[0] == 0
    assert first_token[1] == 'hello'
    assert first_token[2] == 'dave'


def test_tokenize_on_tokens():
    tokens = parser.tokenize(TEXT_WITH_TOKENS, MOCK_TOKENS)
    assert len(tokens) == 2
    first_token = tokens[0]

    assert first_token[0] == 0
    assert first_token[1] == 'hello'
    assert first_token[2] == 'dave '

    second_token = tokens[1]

    assert second_token[0] == 11
    assert second_token[1] == 'NOW'
    assert second_token[2] == ''
