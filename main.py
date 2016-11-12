import json
import asyncio
from slack_today_i_did.bot_file import TodayIDidBot
from slack_today_i_did.bot_repl import ReplBot
from slack_today_i_did.our_repo import ElmRepo
import os
import argparse


def setup():
    config_found = True

    try:
        with open('priv.json') as f:
            data = json.load(f)
    except FileNotFoundError:
        print('not using config file..')
        print('some features may be disabled!')
        config_found = False

    repo = None

    os.makedirs('reports', exist_ok=True)

    if config_found:
        os.makedirs('repos', exist_ok=True)
        github_data = data['github']
        repo = ElmRepo(github_data['folder'], github_data['token'], github_data['org'], github_data['repo'])
    else:
        data = {}

    return (data, repo)


def setup_slack(data, repo):
    return TodayIDidBot(
        data.get('token', ''),
        rollbar_token=data.get('rollbar-token', None),
        elm_repo=repo
    )


def setup_cli(data, repo):
    return ReplBot(
        data.get('token', ''),
        rollbar_token=data.get('rollbar-token', None),
        elm_repo=repo
    )


def main():
    parser = argparse.ArgumentParser(description='Start the slack-today-i-did-bot')

    parser.add_argument(
        '--repl',
        '-r',
        action='store_true',
        help='run the repl',
        default=False
    )
    parser.add_argument(
        '--slack',
        '-s',
        action='store_true',
        help='run the slack bot',
        default=False
    )

    args = parser.parse_args()

    if args.repl and args.slack:
        print('Please only start the repl or the slack bot!')
        exit(-1)

    (data, repo) = setup()

    if args.repl:
        print('starting repl..')
        client = setup_cli(data, repo)
    elif args.slack:
        print('starting slack client..')
        client = setup_slack(data, repo)
    else:
        print('starting slack client..')
        client = setup_slack(data, repo)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main_loop())


if __name__ == '__main__':
    main()
