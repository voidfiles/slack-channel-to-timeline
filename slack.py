#!/usr/bin/env python3

import argparse
import json
import pathlib
import re
import time
import colorama
import requests
import termcolor
import queue
import urllib.parse
import csv
from environs import Env

from datetime import datetime
from typing import List
from multiprocessing import Process, Queue
from slack_sdk import WebClient

env = Env()
env.read_env()  # read .env file, if it exists

cookie = env('SLACK_COOKIE')
token = env('SLACK_TOKEN')

client = WebClient(
    token=token,
    headers={
        "Cookie": f'd={cookie}'
    })
api_response = client.api_test()
assert api_response.get('ok', False)
assert False, api_response
# r = requests.post(
#     "https://slack.com/api/auth.test",
#     params=dict(pretty=1),
#     cookies={
#         "d": urllib.parse.quote(urllib.parse.unquote("xoxd-MMn8UOXcuqJMSSM3rxecmmvaeBifBx%2BMMrONsqED4kDuiqGs3SOiIMgeT8CjzeS2P%2FgHxfn4mwJCHRXgIfg%2BfYxGwlj6r3pL6k2lQ6E634RXHbeVR3LVVhWX0YeS3g5jMO4AMozupKJuXkXIZpJKkbZAjQJgiNXZYoPL4zWJfnr5ohaN7w3GDNQY")),
#     },
#     data={
#         "token": "xoxc-534697187712-2686106030869-4763826039425-51ec3e73ef2310897630d91d071cb10e0d51610ff5add6814aa3aa87ce49b273"
#     }
# ).json()
# print(r)