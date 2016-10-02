import json
from typing import Tuple

class Report(object):
    def __init__(self, channel, name:str, time_to_run: Tuple[int,int], people, wait: Tuple[int, int], time_run=None):
        self.name = name
        self.people_to_bother = people
        self.channel = channel
        self.responses = {}
        self.time_run = time_run
        self.wait_for = wait
        self.time_to_run = time_to_run
        self.is_ended = False
        self.last_day_run = None

    def bother_people(self, client):
        if not self.people_to_bother:
            return

        self.responses = {}
        self.time_run = datetime.datetime.utcnow()
        client.send_channel_message(self.channel, 'Starting my report!')

        for person in self.people_to_bother[:]:
            client.send_message(person, 'Sorry to bother you!')
            self.add_response(person, '')
            self.people_to_bother.remove(person)

    def is_time_to_bother_people(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now_string = time.strftime("%j:%Y %H:%M:", time.gmtime(current_time))

        hour_mins = time_now_string.split(' ')[1].split(':')
        (hours, minutes) = hour_mins[0], hour_mins[1]
        time_now = (int(hours), int(minutes))

        if time_now < self.time_to_run:
            return False

        if self.time_run is not None:
            day_year = time_now_string.split(' ')[0].split(':')
            (day_in_year, year) = day_year[0], day_year[1]
            (time_run_day_in_year, time_run_year) = self.time_run.strftime('%j:%Y').split(':')

            if int(year) ==  int(time_run_year) and int(day_in_year) == int(time_run_day_in_year):
                return False


        self.is_ended = False
        return True

    def is_time_to_end(self) -> bool:
        if self.is_ended:
            return False

        current_time = time.time()
        time_now = time.strftime("%H:%M:", time.gmtime(current_time))
        time_now = (int(time_now.split(':')[0]), int(time_now.split(':')[1]))

        if time_now < (self.time_to_run[0] + self.wait_for[0], self.time_to_run[1] + self.wait_for[1]):
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
        with open(f'reports/report-{self.name}-{self.channel}-{self.time_run}.json', 'w') as f:
            json.dump(self.responses, f)

    def save(self):
        with open(f'reports/report-config-{self.name}-{self.channel}.json', 'w') as f:
            json.dump(f, self.as_dict())

    def as_dict(self):
        return {
            'name' : self.name,
            'channel' : self.channel,
            'responses' : self.responses,
            'people_to_bother' : self.people_to_bother,
            'time_run' : (str(self.time_run) if self.time_run is not None else "")
        }

