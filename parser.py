
def fill_in_the_gaps(message, tokens):
    """
        take things that look like [(12, FOR)] turn into [(12, FOR, noah)]
    """

    if len(tokens) < 1:
        return []

    if len(tokens) == 1:
        start_index = tokens[0][0]
        token = tokens[0][1]

        return [ (start_index, token, message[start_index + len(token) + 1:]) ]

    builds = []

    for (i, (start_index, token)) in enumerate(tokens):
        if i == len(tokens) - 1:
            builds.append((start_index, token, message[start_index + len(token) + 1:]))
            continue


        end_index = tokens[i + 1][0]
        builds.append((start_index, token, message[start_index + len(token) + 1: end_index]))

    return builds


def tokens_with_index(known_tokens, message):
    """ get the tokens out of a message, in order, along with
        the index it was found at
    """

    build = []

    start_index = 0
    end_index = 0
    offset = 0

    for word in message.split(' '):
        if word in known_tokens:
            token = word
            start_index = end_index + message[end_index:].index(token)
            end_index = start_index + len(token)
            build.append((start_index, token))

    return sorted(build, key=lambda x:x[0])


def tokenize(text, known_tokens):
    """ Take text and known tokens
    """

    text = text.strip()
    tokens = fill_in_the_gaps(text, tokens_with_index(known_tokens, text))

    return tokens


def eval(tokens, known_functions, default_args=None):
    # when we can't find anything

    if default_args is None:
        default_args = []

    args = default_args
    errors = []

    if len(tokens) == 0:
        first_function_name = 'error-help'
        args.append(('NO_TOKENS', str))
    # when we have stuff to work with!
    else:
        first_function_name = tokens[0][1]
        first_arg = tokens[0][2].strip()

        if len(first_arg) > 0:
            args.append((first_arg, str))

        if len(tokens) > 1:
            for (start_index, function_name, arg_to_function) in tokens[1:]:
                func = known_functions[function_name]

                try:
                    evaled = func(arg_to_function)
                    args.append((evaled, func.__annotations__.get('return', None)))
                except Exception as e:
                    errors.append((function_name, e))

    return {
        'action': known_functions[first_function_name],
        'args' : args,
        'errors': errors
    }



def exception_error_messages(errors) -> str:
    message = f'I got the following errors:\n'
    message += '```\n'
    message += '\n'.join(f'- {func_name} threw {error}' for (func_name, error) in errors)
    message += '\n```'

    return message

def mismatching_args_messages(action, annotations, args) -> str:
    message = f'I wanted things to look like for function `{action.__name__}`:\n'
    message += '```\n'
    message += '\n'.join(f'- {arg_name} : {type}' for (arg_name, type) in annotations.items())
    message += '\n```'

    message += "\nBut you gave me:\n"
    message += '```\n'
    message += '\n'.join(f'- {arg} : {type}' for (arg, type) in args)
    message += '\n```'

    if len(annotations) < len(args):
        return f'too many args too many many args\n{message}'
    else:
        return f'we need some more args in here! we need some more args in here\n{message}'

def mismatching_types_messages(action, annotations, args) -> str:
    messages = []

    for ((arg, type), (arg_name, annotation)) in zip(args, annotations.items()):
        if type != annotation:
            messages.append(f'Type mistmach for function `{action.__name__}')
            messages.append(f'You tried to give me a `{type}` but I wanted a `{annotation}` for the arg `{arg_name}`!')

    return '\n'.join(messages)
