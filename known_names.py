import json
from typing import List, Tuple

class KnownNames(object):
    """ Alias a person to a group of names, with saving and loading from disk
    """
    def __init__(self):
        self.people = {}

    def add_name(self, person: str, name: str) -> None:
        if person not in self.people:
            self.people[person] = []

        self.people[person].append(name)

    def get_names(self, person: str) -> List[str]:
        return self.people.get(person, [])

    def load_from_file(self, filename: str) -> None:
        try:
            with open(filename) as f:
                as_json = json.load(f)
        except FileNotFoundError:
            return

        for (person, names) in as_json['people'].items():
            self.people[person] = names

    def save_to_file(self, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump({ 'people' :  self.people }, f)

