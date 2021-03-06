from typing import Any, TypeVar, Callable, Dict, List, Tuple, NamedTuple, Union
import copy
import functools

# tokenizer types
Token = Tuple[int, str]
TokenAndRest = Tuple[int, str, str]

# parser types
FuncArg = Union['Constant', 'FuncCall']
Constant = NamedTuple(
    'Constant',
    [('value', Any), ('return_type', type)])
FuncCall = NamedTuple(
    'FuncCall',
    [('func_name', str), ('args', List[FuncArg]), ('return_type', type)])
FuncCallBinding = NamedTuple(
    'FuncCallBinding',
    [('func_call', FuncCall), ('evaluate', Callable[[FuncCall, List[FuncArg]], 'FuncResult'])])
FuncResult = NamedTuple(
    'FuncResult',
    [('result', Any), ('return_type', type), ('action', Callable), ('args', List[Any]), ('errors', List[str])])
ArgsResult = NamedTuple(
    'ArgsResult',
    [('result', List[Any]), ('return_types', List[type]), ('errors', List[str])])
FunctionMap = Dict[str, Callable]


def metafunc(fn):
    fn.is_metafunc = True
    return fn


def is_metafunc(fn):
    return getattr(fn, 'is_metafunc', False)


def fill_in_the_gaps(message: str, tokens: List[Token]) -> List[TokenAndRest]:
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


def tokens_with_index(known_tokens: List[str], message: str) -> List[Token]:
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


def tokenize(text: str, known_tokens: List[str]) -> List[TokenAndRest]:
    """ Take text and known tokens
    """

    text = text.strip()
    tokens = fill_in_the_gaps(text, tokens_with_index(known_tokens, text))

    return tokens


def parse(tokens: List[TokenAndRest], known_functions: FunctionMap) -> FuncCallBinding:
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

    return FuncCallBinding(
        FuncCall(first_function_name, args, return_type),
        evaluator)


def evaluate_func_call(
        known_functions: FunctionMap,
        func_call: FuncCall,
        default_args: List[FuncArg] = []) -> FuncResult:
    """ Evaluate `func_call` in the context of `known_functions`
        after prepending `default_args` to `func_call`'s arguments
    """
    action = known_functions[func_call.func_name]

    if is_metafunc(action):
        args = default_args + [Constant(func_call.args, List[FuncArg])]
    else:
        args = default_args + func_call.args

    args_result = evaluate_args(known_functions, args)

    if len(args_result.errors) > 0:
        return FuncResult(None, None, None, [], args_result.errors)

    argument_errors = []

    # TODO: simply copy.deepcopy and pop('return', None) after
    # https://github.com/python/typing/issues/306 is resolved.
    # `-> ChannelMessages` blows up if you try to copy.deepcopy the annotations.
    annotations = dict(action.__annotations__)
    return_type = annotations.pop('return', None)
    annotations = copy.deepcopy(annotations)

    # check arity mismatch
    num_keyword_args = len(action.__defaults__) if action.__defaults__ else 0
    num_positional_args = len(annotations) - num_keyword_args
    if num_positional_args > len(args_result.result):
        argument_errors.append(
            mismatching_args_messages(
                action,
                annotations,
                args_result.result,
                args_result.return_types
            )
        )

    mismatching_types = mismatching_types_messages(
        action,
        annotations,
        args_result.result,
        args_result.return_types
    )

    if len(mismatching_types) > 0:
        argument_errors.append(mismatching_types)

    if len(argument_errors) > 0:
        return FuncResult(None, None, None, [], argument_errors)

    try:
        return FuncResult(action(*args_result.result), return_type, action, args_result.result, [])
    except Exception as e:
        error_message = exception_error_messages([(func_call.func_name, e)])
        return FuncResult(None, None, None, [], [error_message])


def evaluate_args(
        known_functions: FunctionMap,
        args: List[FuncArg]) -> ArgsResult:
    result = []
    return_types = []
    all_errors = []

    for arg in args:
        if isinstance(arg, Constant):
            result.append(arg.value)
            return_types.append(arg.return_type)
        elif isinstance(arg, FuncCall):
            func_result = evaluate_func_call(known_functions, arg)
            result.append(func_result.result)
            return_types.append(func_result.return_type)

            if len(func_result.errors) > 0:
                all_errors.extend(func_result.errors)

    return ArgsResult(result, return_types, all_errors)


def exception_error_messages(errors) -> str:
    message = f'I got the following errors:\n'
    message += '```\n'

    message += '\n'.join(
        f'- {func_name} threw {error}' for (func_name, error) in errors
    )

    message += '\n```'

    return message


def mismatching_args_messages(action, annotations, arg_values, arg_types) -> str:
    message = f'I wanted things to look like for function `{action.__name__}`:\n'  # noqa: E501
    message += '```\n'

    message += '\n'.join(
        f'- {arg_name} : {arg_type}' for (arg_name, arg_type) in annotations.items()
    )

    message += '\n```'

    message += "\nBut you gave me:\n"
    message += '```\n'
    message += '\n'.join(f'- {arg_value} : {arg_type}'
                         for (arg_value, arg_type) in zip(arg_values, arg_types))
    message += '\n```'

    if len(annotations) < len(arg_values):
        return f'Too many arguments!\n{message}'
    else:
        return f'Need some more arguments!\n{message}'


def mismatching_types_messages(action, annotations, arg_values, arg_types) -> str:
    messages = []

    for (arg_value, arg_type, (arg_name, annotation)) in zip(arg_values, arg_types, annotations.items()):
        if annotation == Any or isinstance(annotation, TypeVar):
            continue

        if arg_type != annotation:
            messages.append(f'Type mistmach for function `{action.__name__}`')
            messages.append(
                f'You tried to give me a `{arg_type}` but I wanted a `{annotation}` for the arg `{arg_name}`!'  # noqa: E501
            )

    return '\n'.join(messages)
