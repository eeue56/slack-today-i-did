from typing import Any, TypeVar, List, NamedTuple, Union
import functools


Constant = NamedTuple('Constant', [('value', Any), ('return_type', type)])
FuncCall = NamedTuple('FuncCall', [('func_name', str), ('args', List[str]), ('return_type', type)])
TopLevelArg = Union[Constant, FuncCall]


def metafunc(fn):
    fn.is_metafunc = True
    return fn


def is_metafunc(fn):
    return getattr(fn, 'is_metafunc', False)


def fill_in_the_gaps(message, tokens):
    """
        take things that look like [(12, FOR)] turn into [(12, FOR, noah)]
    """

    if len(tokens) < 1:
        return []

    if len(tokens) == 1:
        start_index = tokens[0][0]
        token = tokens[0][1]
        bits_after_token = message[start_index + len(token) + 1:]

        return [(start_index, token, bits_after_token)]

    builds = []

    for (i, (start_index, token)) in enumerate(tokens):
        if i == len(tokens) - 1:
            bits_after_token = message[start_index + len(token) + 1:]
            builds.append((start_index, token, bits_after_token))
            continue

        end_index = tokens[i + 1][0]
        bits_after_token = message[start_index + len(token) + 1: end_index]
        builds.append((start_index, token, bits_after_token))

    return builds


def tokens_with_index(known_tokens, message):
    """ get the tokens out of a message, in order, along with
        the index it was found at
    """

    build = []

    start_index = 0
    end_index = 0

    for word in message.split(' '):
        if word in known_tokens:
            token = word
            start_index = end_index + message[end_index:].index(token)
            end_index = start_index + len(token)
            build.append((start_index, token))

    return sorted(build, key=lambda x: x[0])


def tokenize(text, known_tokens):
    """ Take text and known tokens
    """

    text = text.strip()
    tokens = fill_in_the_gaps(text, tokens_with_index(known_tokens, text))

    return tokens


def parse(tokens, known_functions, default_args=None):
    if default_args is None:
        default_args = []

    more_args = []

    # when we can't find anything
    if len(tokens) == 0:
        first_function_name = 'error-help'
        more_args.append(Constant('NO_TOKENS', str))
    # when we have stuff to work with!
    else:
        first_function_name = tokens[0][1]
        first_arg = tokens[0][2].strip()

        if len(first_arg) > 0:
            more_args.append(Constant(first_arg, str))

        if len(tokens) > 1:
            for (start_index, function_name, arg_to_function) in tokens[1:]:
                func = known_functions[function_name]
                actual_arg = [arg_to_function] if len(arg_to_function) > 0 else []
                return_type = func.__annotations__.get('return', None)
                more_args.append(FuncCall(function_name, actual_arg, return_type))

    action = known_functions[first_function_name]
    evaluator = functools.partial(evaluate, known_functions)

    if is_metafunc(action):
        args = []
        args.extend(default_args)
        args.append(Constant(more_args, List[TopLevelArg]))
    else:
        args = default_args + more_args

    return {
        'action': action,
        'args': args,
        'evaluate': evaluator,
    }


def evaluate(known_functions, args):
    result = []
    errors = []

    for arg in args:
        if isinstance(arg, Constant):
            result.append(arg.value)
        elif isinstance(arg, FuncCall):
            try:
                result.append(known_functions[arg.func_name](*arg.args))
            except Exception as e:
                errors.append((arg.func_name, e))

    return {
        'args': result,
        'errors': errors,
    }


def exception_error_messages(errors) -> str:
    message = f'I got the following errors:\n'
    message += '```\n'

    message += '\n'.join(
        f'- {func_name} threw {error}' for (func_name, error) in errors
    )

    message += '\n```'

    return message


def mismatching_args_messages(action, annotations, args) -> str:
    message = f'I wanted things to look like for function `{action.__name__}`:\n'  # noqa: E501
    message += '```\n'

    message += '\n'.join(
        f'- {arg_name} : {arg_type}' for (arg_name, arg_type) in annotations.items()
    )

    message += '\n```'

    message += "\nBut you gave me:\n"
    message += '```\n'
    message += '\n'.join(f'- {arg} : {arg_type}' for (arg, arg_type) in args)
    message += '\n```'

    if len(annotations) < len(args):
        return f'Too many arguments!\n{message}'
    else:
        return f'Need some more arguments!\n{message}'


def mismatching_types_messages(action, annotations, args) -> str:
    messages = []

    for (arg, (arg_name, annotation)) in zip(args, annotations.items()):
        if annotation != Any and not isinstance(annotation, TypeVar):
            continue

        if arg.return_type != annotation:
            messages.append(f'Type mistmach for function `{action.__name__}`')
            messages.append(
                f'You tried to give me a `{arg.return_type}` but I wanted a `{annotation}` for the arg `{arg_name}`!'  # noqa: E501
            )

    return '\n'.join(messages)
