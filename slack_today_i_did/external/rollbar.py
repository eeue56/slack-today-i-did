"""
A file for dealing with rollbar related things
"""
import requests


class Rollbar(object):
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.rollbar.com"

    def request(self, url):
        actual_url = self.base_url + url + f"?access_token={self.token}"
        return requests.get(actual_url)

    def get_item_by_id(self, id):
        response = self.request(f'/api/1/item/{id}')

        json = response.json()

        return json

    def get_item_by_counter(self, counter):
        response = self.request(f'/api/1/item_by_counter/{counter}')

        json = response.json()

        return json['result']
