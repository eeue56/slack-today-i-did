from typing import Any, TypeVar, Callable, List, NamedTuple, Union
import copy
import functools


FuncArg = Union['Constant', 'FuncCall']
Constant = NamedTuple('Constant', [('value', Any), ('return_type', type)])
FuncCall = NamedTuple('FuncCall', [('func_name', str), ('args', List[FuncArg]), ('return_type', type)])
FuncResult = NamedTuple(
    'FuncResult',
    [('result', Any), ('action', Callable), ('args', List[Any]), ('errors', List[str])])


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


def parse(tokens, known_functions):
    args = []

    # when we can't find anything
    if len(tokens) == 0:
        first_function_name = 'error-help'
        args.append(Constant('NO_TOKENS', str))
    # when we have stuff to work with!
    else:
        first_function_name = tokens[0][1]
        first_arg = tokens[0][2].strip()

        if len(first_arg) > 0:
            args.append(Constant(first_arg, str))

        if len(tokens) > 1:
            for (start_index, function_name, arg_to_function) in tokens[1:]:
                func = known_functions[function_name]
                actual_arg = [Constant(arg_to_function, str)] if len(arg_to_function) > 0 else []
                return_type = func.__annotations__.get('return', None)
                args.append(FuncCall(function_name, actual_arg, return_type))

    action = known_functions[first_function_name]
    return_type = action.__annotations__.get('return', None)
    evaluator = functools.partial(evaluate_func_call, known_functions)

    return {
        'func_call': FuncCall(first_function_name, args, return_type),
        'evaluate': evaluator,
    }


def evaluate_func_call(known_functions, func_call, default_args=[]) -> FuncResult:
    all_errors = []
    action = known_functions[func_call.func_name]

    if is_metafunc(action):
        args = default_args + [Constant(func_call.args, List[FuncArg])]
    else:
        args = default_args + func_call.args

    args_evaluation = evaluate_args(known_functions, args)
    evaluated_args = args_evaluation['args']

    if len(args_evaluation['errors']) > 0:
        all_errors.extend(args_evaluation['errors'])
        return FuncResult(None, None, [], all_errors)

    argument_errors = []

    # TODO: simply copy.deepcopy and pop('return', None) after
    # https://github.com/python/typing/issues/306 is resolved.
    # `-> ChannelMessages` blows up if you try to copy.deepcopy the annotations.
    annotations = dict(action.__annotations__)
    annotations.pop('return', None)
    annotations = copy.deepcopy(annotations)

    # check arity mismatch
    num_keyword_args = len(action.__defaults__) if action.__defaults__ else 0
    num_positional_args = len(annotations) - num_keyword_args
    if num_positional_args > len(evaluated_args):
        argument_errors.append(
            mismatching_args_messages(action, annotations, evaluated_args)
        )

    mismatching_types = mismatching_types_messages(
        action,
        annotations,
        evaluated_args
    )

    if len(mismatching_types) > 0:
        argument_errors.append(mismatching_types)

    if len(argument_errors) > 0:
        all_errors.extend(argument_errors)
        return FuncResult(None, None, [], all_errors)

    try:
        return FuncResult(action(*evaluated_args), action, evaluated_args, all_errors)
    except Exception as e:
        return FuncResult(None, None, [], [exception_error_messages([(func_call.func_name, e)])])


def evaluate_args(known_functions, args, default_args=[]):
    result = []
    all_errors = []

    for arg in default_args + args:
        if isinstance(arg, Constant):
            result.append(arg.value)
        elif isinstance(arg, FuncCall):
            func_result = evaluate_func_call(known_functions, arg)
            result.append(func_result.result)

            if len(func_result.errors) > 0:
                all_errors.extend(func_result.errors)

    return {
        'args': result,
        'errors': all_errors,
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
