import json
from typing import Tuple, Dict, Any
import time
import datetime


class Report(object):
    def __init__(
            self,
            channel: str,
            name: str,
            time_to_run: Tuple[int, int],
            people,
            wait: Tuple[int, int],
            time_run=None,
            reports_dir='reports',
    ):
        self.name = name
        self.people_to_bother = people
        self.channel = channel
        self.responses = {}
        self.time_run = time_run
        self.wait_for = wait
        self.time_to_run = time_to_run
        self.reports_dir = reports_dir
        self.is_ended = False
        self.last_day_run = None

    def bother_people(self):
        if not self.people_to_bother:
            return []

        self.responses = {}
        self.time_run = datetime.datetime.utcnow()
        messages = []
        messages.append((self.channel, 'Starting my report!'))

        for person in self.people_to_bother[:]:
            messages.append((person, 'Sorry to bother you!'))
            self.add_response(person, '')
            self.people_to_bother.remove(person)

        return messages

    def is_time_to_bother_people(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now_string = time.strftime(
            "%j:%Y %H:%M:",
            time.gmtime(current_time)
        )

        hour_mins = time_now_string.split(' ')[1].split(':')
        (hours, minutes) = hour_mins[0], hour_mins[1]
        time_now = (int(hours), int(minutes))

        if time_now < self.time_to_run:
            return False

        if self.time_run is not None:
            day_year = time_now_string.split(' ')[0].split(':')
            (day_in_year, year) = day_year[0], day_year[1]
            (time_run_day_in_year, time_run_year) = self.time_run.strftime('%j:%Y').split(':')  # noqa: E501

            if int(year) == int(time_run_year) and int(day_in_year) == int(time_run_day_in_year):  # noqa: E501
                return False

        self.is_ended = False
        return True

    def is_time_to_end(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now = time.strftime("%H:%M:", time.gmtime(current_time))
        time_now = (int(time_now.split(':')[0]), int(time_now.split(':')[1]))

        end_time = (self.time_to_run[0] + self.wait_for[0], self.time_to_run[1] + self.wait_for[1])  # noqa: E501

        if time_now < end_time:
            return False

        self.is_ended = True
        return True

    def is_for_user(self, user):
        return user in self.responses or user in self.people_to_bother

    def add_response(self, user, message):
        if user not in self.responses:
            self.responses[user] = message
        else:
            if len(self.responses[user]) == 0:
                self.responses[user] = message
            else:
                self.responses[user] += '\n' + message
        self.save_responses()

    def save_responses(self):
        with open(f'{self.reports_dir}/report-{self.name}-{self.channel}-{self.time_run}.json', 'w') as f:  # noqa: E501
            json.dump(self.responses, f)

    def save(self):
        with open(f'{self.reports_dir}/report-config-{self.name}-{self.channel}.json', 'w') as f:  # noqa: E501
            json.dump(f, self.as_dict())

    def as_dict(self):
        return {
            'name': self.name,
            'channel': self.channel,
            'responses': self.responses,
            'people_to_bother': self.people_to_bother,
            'time_run': (str(self.time_run) if self.time_run is not None else "")  # noqa: E501
        }


class Sessions(object):
    def __init__(self):
        self.sessions = {}

    def has_running_session(self, person: str) -> bool:
        if person not in self.sessions:
            return False

        return self.sessions[person]['is_running']

    def start_session(self, person: str, channel: str) -> None:
        self.sessions[person] = {
            'is_running': True,
            'messages': [],
            'channel': channel
        }

    def end_session(self, person: str) -> None:
        if not self.has_running_session(person):
            return

        self.sessions[person]['is_running'] = False

    def add_message(self, person: str, message: str) -> None:
        if not self.has_running_session(person):
            return

        self.sessions[person]['messages'].append(message)

    def get_entry(self, person: str) -> Dict[str, Any]:
        if person not in self.sessions:
            return {}

        return self.sessions[person]

    def retire_session(self, person: str, filename: str) -> None:
        session_info = self.sessions.pop(person)

        with open(filename, 'w') as f:
            json.dump(session_info, f)

    def load_from_file(self, filename: str) -> None:
        """ Load people:session from a file """
        try:
            with open(filename) as f:
                as_json = json.load(f)
        except FileNotFoundError:
            return

        for (name, session) in as_json['sessions'].items():
            self.sessions[name] = session

    def save_to_file(self, filename: str) -> None:
        """ save people:sessions to a file """
        with open(filename, 'w') as f:
            json.dump({'sessions': self.sessions}, f)
