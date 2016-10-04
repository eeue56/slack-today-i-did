class CommandHistory(object):
    def __init__(self):
        self.history = {}

    def add_command(self, channel, command, args):
        if channel not in self.history:
            self.history[channel] = []

        self.history[channel].append({ 'action': command, 'args': args })

    def last_command(self, channel):
        if channel not in self.history:
            return None
        return self.history[channel][-1]
