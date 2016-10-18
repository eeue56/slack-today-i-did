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


def test_eval_no_tokens():
    known_funcs = {'error-help': lambda x:x}
    stuff = parser.eval([], known_funcs)

    assert stuff['action'] == known_funcs['error-help']
    assert stuff['args'] == [('NO_TOKENS', str)]
    assert stuff['errors'] == []


def test_eval_help_not_in_known_funcs():
    # `eval` trusts tokenize to have extracted
    # only known function names into tokens
    with pytest.raises(KeyError):
        stuff = parser.eval([(0, 'help', ''), (0, 'hello', 'dave')], MOCK_TOKENS)


def test_eval_help_with_arg():
    funcs_with_help = dict(MOCK_TOKENS, help=lambda x:x)
    tokens = parser.tokenize('help ' + TEXT_WITH_TOKENS, funcs_with_help)
    stuff = parser.eval(tokens, funcs_with_help)

    assert stuff['action'] == funcs_with_help['help']
    assert stuff['args'] == [('hello', str), ('NOW', str)]
    assert stuff['errors'] == []


def test_eval_first_func_with_one_arg():
    known_funcs = {'hello': lambda x:x}
    stuff = parser.eval([(0, 'hello', 'world')], known_funcs)

    assert stuff['action'] == known_funcs['hello']
    assert stuff['args'] == [('world', str)]
    assert stuff['errors'] == []


def test_eval_second_func_with_one_arg():
    known_funcs = {'cocoa': lambda x:x + 'cocoa', 'double': lambda x:x * 2}
    known_funcs['double'].__annotations__['return'] = str

    stuff = parser.eval([(0, 'cocoa', ''), (0, 'double', 'cream')], known_funcs)

    assert stuff['action'] == known_funcs['cocoa']
    assert stuff['args'] == [('creamcream', str)]
    assert stuff['errors'] == []


def test_eval_second_func_with_error():
    known_funcs = {'cocoa': lambda x:x + 'cocoa', 'koan': lambda x: 1 / 0}

    stuff = parser.eval([(0, 'cocoa', ''), (0, 'koan', '')], known_funcs)

    assert stuff['action'] == known_funcs['cocoa']
    assert stuff['args'] == []
    assert len(stuff['errors']) == 1
    assert stuff['errors'][0][0] == 'koan'
    assert isinstance(stuff['errors'][0][1], ZeroDivisionError)
