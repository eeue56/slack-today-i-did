import json
from typing import List, Tuple

import re

class Notification(object):

    def __init__(self):
        self.patterns = {}

    def add_pattern(self, person: str, pattern: str):
        if person not in self.patterns:
            self.patterns[person] = []

        self.patterns[person].append(pattern)

    def who_wants_it(self, text):
        who_wants_it = []

        for (person, patterns) in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.MULTILINE) is not None:
                    who_wants_it.append(person)
                    break

        return who_wants_it

    def get_patterns(self, person: str) -> List[str]:
        if person in self.patterns:
            return self.patterns[person]
        return []

    def load_from_file(self, filename: str):
        try:
            with open(filename) as f:
                as_json = json.load(f)
        except FileNotFoundError:
            return

        for (name, patterns) in as_json['patterns'].items():
            self.patterns[name] = patterns

    def save_to_file(self, filename: str):
        with open(filename, 'w') as f:
            json.dump({ 'patterns' :  self.patterns }, f)


