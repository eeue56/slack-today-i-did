from typing import List
import re

from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
from slack_today_i_did.notify import Notification


class NotifyExtensions(BotExtension):
    def _setup_extension(self) -> None:
        self.notify = Notification()
        self.notify.load_from_file(self.notify_file)

    def when_you_hear(self, channel: str, pattern: str) -> ChannelMessages:
        """ notify the user when you see a pattern """
        person = self._last_sender

        try:
            re.compile(pattern)
        except Exception as e:
            return ChannelMessage(channel, f'Invalid regex due to {e.msg}')

        self.notify.add_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)
        return ChannelMessage(
            channel,
            f'Thanks! You be notified when I hear that pattern. Use `forget` to stop me notifying you!'
        )

    def stop_listening(self, channel: str, pattern: str) -> ChannelMessages:
        """ stop notify the user when you see a pattern """
        person = self._last_sender

        self.notify.forget_pattern(person, pattern)
        self.notify.save_to_file(self.notify_file)

        return []

    def ping_person(self, channel: str, person: str) -> ChannelMessages:
        """ notify a person about a message. Ignore direct messages """
        if self.is_direct_message(channel):
            return

        return ChannelMessage(channel, f"<@{person}> ^")

    def _parse_message(self, channel: str, strings: List[str]) -> None:
        if self.notify is None:
            return

        people_who_want_notification = []

        for string in strings:
            people_who_want_notification.extend(self.notify.who_wants_it(string))

        people_who_want_notification = set(people_who_want_notification)

        for person in people_who_want_notification:
            self.ping_person(channel, person)
