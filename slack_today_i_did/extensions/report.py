import datetime
from typing import List

from slack_today_i_did.reports import Report
from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages


class ReportExtensions(BotExtension):
    def responses(self, channel: str) -> ChannelMessages:
        """ list the last report responses for the current channel """

        if channel not in self.reports:
            return ChannelMessage(
                channel,
                f'No reports found for channel {channel}'
            )

        message = ""
        for report in self.reports[channel].values():
            message += f'for the report: {report.name}'
            message += '\n\n'.join(
                f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
            )

        return ChannelMessage(channel, message)

    def report_responses(self, channel: str, name: str) -> ChannelMessages:
        """ list the last report responses for the current channel """

        name = name.strip()

        if channel not in self.reports or name not in self.reports[channel]:
            return ChannelMessage(
                channel,
                f'No reports found for channel {channel}'
            )

        return self.single_report_responses(channel, self.reports[channel][name])

    def single_report_responses(self, channel: str, report) -> ChannelMessages:
        """ Send info on a single response """
        message = '\n\n'.join(
            f'User {user} responded with:\n{response}' for (user, response) in report.responses.items()  # noqa: E501
        )

        if message == '':
            message = f'Nobody replied to the report {report.name}'
        else:
            message = f'For the report: {report.name}\n' + message
        return ChannelMessage(channel, message)

    def bother(self, channel: str, name: str, users: List[str], at: datetime.datetime, wait: datetime.datetime) -> ChannelMessages:  # noqa: E501
        """ add a report for the given users at a given time,
            reporting back in the channel requested
        """
        time_to_run = (at.hour, at.minute)
        wait_for = (wait.hour, wait.minute)
        self.add_report(Report(channel, name, time_to_run, users, wait_for, reports_dir=self.reports_dir))
        return []

    def bother_all_now(self, channel: str) -> ChannelMessages:
        """ run all the reports for a channel
        """
        messages = []
        for report in self.reports.get(channel, {}).values():
            bothers = [ChannelMessage(*bother) for bother in report.bother_people()]
            messages.extend(bothers)
        return messages

    def add_report(self, report):
        if report.channel not in self.reports:
            self.reports[report.channel] = {}
        self.reports[report.channel][report.name] = report
