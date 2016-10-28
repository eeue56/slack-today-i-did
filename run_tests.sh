#! /usr/bin/env bash
set -e

# make sure that there's no syntax errors
python3 -c "import main"

# run flake8 on everything
flake8 main.py slack_today_i_did

# run doctest
python3 -m doctest slack_today_i_did/*.py

python3 -m pytest
