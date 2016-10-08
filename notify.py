import json
from typing import List
import re


class Notification(object):
    """ Allows you to register multiple regex patterns with a person
        This is designed to let you notify users based on an incoming pattern
    """

    def __init__(self):
        self.patterns = {}

    def add_pattern(self, person: str, pattern: str) -> None:
        """ register a pattern to notify a given person
        """
        
        if person not in self.patterns:
            self.patterns[person] = []

        self.patterns[person].append(pattern)


    def forget_pattern(self, person: str, pattern: str) -> None:
        """ stop notifying a person for a given pattern 
        """

        if person not in self.patterns:
            return

        if pattern in self.patterns[person]:
            self.patterns[person].remove(pattern)

    def who_wants_it(self, text: str) -> None:
        """ returns a list of people that want to be notified by 
            a message that matches any of the registered patterns
        """
        who_wants_it = []

        for (person, patterns) in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.MULTILINE) is not None:
                    who_wants_it.append(person)
                    break

        return who_wants_it

    def get_patterns(self, person: str) -> List[str]:
        """ get a list of patterns for a person
        """
        if person in self.patterns:
            return self.patterns[person]
        return []

    def load_from_file(self, filename: str) -> None:
        """ Load people:patterns from a file """
        try:
            with open(filename) as f:
                as_json = json.load(f)
        except FileNotFoundError:
            return

        for (name, patterns) in as_json['patterns'].items():
            self.patterns[name] = patterns

    def save_to_file(self, filename: str) -> None:
        """ save people:patterns to a file """
        with open(filename, 'w') as f:
            json.dump({'patterns': self.patterns}, f)
