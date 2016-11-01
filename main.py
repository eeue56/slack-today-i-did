import json
import asyncio
from slack_today_i_did.bot_file import TodayIDidBot
from slack_today_i_did.bot_repl import ReplBot
from slack_today_i_did.our_repo import ElmRepo
import os


def setup():
    os.makedirs('reports', exist_ok=True)
    os.makedirs('repos', exist_ok=True)

    with open('priv.json') as f:
        data = json.load(f)

    github_data = data['github']
    repo = ElmRepo(github_data['folder'], github_data['token'], github_data['org'], github_data['repo'])

    return TodayIDidBot(data['token'], rollbar_token=data['rollbar-token'], elm_repo=repo)

def setup_cli():
    os.makedirs('reports', exist_ok=True)
    os.makedirs('repos', exist_ok=True)

    with open('priv.json') as f:
        data = json.load(f)

    github_data = data['github']
    repo = ElmRepo(github_data['folder'], github_data['token'], github_data['org'], github_data['repo'])

    return ReplBot(data['token'], rollbar_token=data['rollbar-token'], elm_repo=repo)

def main():
    client = setup_cli()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main_loop())


if __name__ == '__main__':
    main()
