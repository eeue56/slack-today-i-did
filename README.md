# slack-today-i-did

A chat-ops bot designed around the principle of ensuring that types for functions are correct.


## Features

- slack and repl support
- live-reload of functions
- live-reload of the entire project
- type safe interactions
- useful error hints
- enable/disable features at runtime
- command history

## Setup

- You must have Python 3.6 installed
- Use virtualenv
- To install deps run `pip install -r requirements.txt`

- In order to use this bot, you must create a file called `priv.json` which looks like this:
```
{
    "token": "<SLACK_BOT_TOKEN>",
    "rollbar-token" : "<ROLLBAR_READ_TOKEN>",
    "github" : {
        "token" : "<GITHUB_OAUTH_TOKEN",
        "repo" : "NoRedInk",
        "org" : "NoRedInk",
        "folder" : "repos"
    }
}

```

## Running

- `python main.py` starts up the slack bot by default
- `python main.py --repl` starts up the local repl


