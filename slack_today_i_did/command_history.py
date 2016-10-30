from slack_today_i_did.type_aware import json


def makes_state_change(f):
    def wrapper(self, *args, **kwargs):
        f(self, *args, **kwargs)
        self.needs_save = True
    return wrapper


def saves_state(f):
    def wrapper(self, *args, **kwargs):
        f(self, *args, **kwargs)
        self.needs_save = False
    return wrapper


class CommandHistory(object):

    @saves_state
    def __init__(self):
        self.history = {}

    @makes_state_change
    def add_command(self, channel, command, args):
        if channel not in self.history:
            self.history[channel] = []

        self.history[channel].append({'action': command, 'args': args})

    def last_command(self, channel):
        if channel not in self.history:
            return None
        return self.history[channel][-1]

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        for channel in self.history:
            if channel not in other.history:
                return False

            if self.history[channel] != other.history[channel]:
                return False

        return True

    @saves_state
    def load_from_file(self, known_tokens, known_types, filename: str) -> None:
        """ Load command history from a file """
        try:
            with open(filename) as f:
                as_json = json.load(f, known_types=known_types)
        except FileNotFoundError:
            return

        for (channel, commands) in as_json['channels'].items():
            for command_entry in commands:
                command_entry = self._command_entry_from_json(known_tokens, command_entry)
                self.add_command(channel, command_entry['action'], command_entry['args'])

    @saves_state
    def save_to_file(self, filename: str) -> None:
        """ save command history to a file """
        with open(filename, 'w') as f:
            channels = {
                'channels': {
                    channel: [self._command_entry_to_json(command) for command in commands]
                    for (channel, commands) in self.history.items()
                }
            }

            json.dump(channels, f)

        self.needs_save = False

    def _command_entry_to_json(self, command_entry):
        action = command_entry['action'].__name__

        return {
            'action': action,
            'args': command_entry['args']
        }

    def _no_longer_exists(self, *args, **kwargs) -> str:
        return 'this thing no longer exists!'

    def _command_entry_from_json(self, known_tokens, json):
        return {
            'action': known_tokens.get(json['action'], self._no_longer_exists),
            'args': json['args']
        }
