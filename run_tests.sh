#! /usr/bin/env bash
set -e

echo "importing main..."
# make sure that there's no syntax errors
python3 -c "import main"

echo "running flake8..."
# run flake8 on everything
flake8 main.py slack_today_i_did

echo "running doctest..."
# run doctest
python3 -m doctest slack_today_i_did/*.py

echo "running pytest..."
python3 -m pytest
