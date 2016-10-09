#! /usr/bin/env bash

# make sure that there's no syntax errors
python3 -c "import main"

# run flake8 on everything
flake8 .

# run doctest
python3 -m doctest *.py **/*.py