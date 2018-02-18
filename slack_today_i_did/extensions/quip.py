import os

import slack_today_i_did.external.quip as quip
from slack_today_i_did.generic_bot import BotExtension


QUIP_API_KEY = os.getenv('QUIP_API_KEY', None)


class QuipExtensions(BotExtension):
    def _setup_extension(self):
        self.quip_client = None
        if QUIP_API_KEY is None:
            return

        self.quip_client = quip.QuipClient(QUIP_API_KEY)

    def _fetch_quip_doc(self, quip_id: str) -> str:
        if self.quip_client is None:
            return None

        return self.quip_client.get_thread(quip_id)
