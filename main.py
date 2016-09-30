import json
import asyncio
from bot_file import TodayIDidBot
from our_repo import ElmRepo
import os

def setup():
    os.mkdir('reports', exist_ok=True)
    os.mkdir('repos', exist_ok=True)

    with open('priv.json') as f:
        data = json.load(f)

    github_data = data['github']
    repo = ElmRepo(github_data['folder'], github_data['token'], github_data['org'], github_data['repo'])

    return TodayIDidBot(data['token'], rollbar_token=data['rollbar-token'], elm_repo=repo)

def main():
    client = setup()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main_loop())


if __name__ == '__main__':
    main()
