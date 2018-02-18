import json

from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages


class RollbarExtensions(BotExtension):
    def rollbar_item(self, channel: str, field: str, counter: int) -> ChannelMessages:
        """ takes a counter, gets the rollbar info for that counter """

        rollbar_info = self.rollbar.get_item_by_counter(counter)

        if field == '' or field == 'all':
            pretty = json.dumps(rollbar_info, indent=4)
        else:
            pretty = rollbar_info.get(
                field,
                f'Could not find the field {field}'
            )

        return ChannelMessage(channel, f'{pretty}')
