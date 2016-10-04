import json
from typing import List, Tuple

class KnownNames(object):
    def __init__(self):
        self.people = {}

    def add_name(self, person: str, name: str):
        if person not in self.people:
            self.people[person] = []

        self.people[person].append(name)

    def get_names(self, person: str) -> List[str]:
        if person in self.people:
            return self.people[person]
        return []

    def load_from_file(self, filename: str):
        with open(filename) as f:
            as_json = json.load(f)

        for (person, names) in as_json['people'].items():
            self.people[person] = names

    def save_to_file(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(f, { 'people' :  self.people })


