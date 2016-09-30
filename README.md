# slack-today-i-did

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

- You can then run it via `python main.py`


