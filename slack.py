#!/usr/bin/env python3

import argparse
from datetime import datetime, date, timedelta
import json
import re
import json
import os
import mimetypes
import base64
from slack_down import convert
import requests
import hashlib
from typing import Union
from environs import Env
from jinja2 import Environment, FileSystemLoader, select_autoescape
from htmldocx import HtmlToDocx

from slack_sdk import WebClient
from dataclasses import dataclass, is_dataclass, asdict

USERNAME_RE = re.compile(r'<@([^>]*)>')
LINK_RE = re.compile(r'<([^>]*)>')
CACHE_DIR = ".cache"

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)

def process_text_for_username(text: str, users: dict):

    def replace_with_link(mat):
        user = users.get(mat.group(1))
        if not user:
            return mat.group(1)

        b = "@" + (user.name or mat.group(1))

        return b

    return USERNAME_RE.sub(replace_with_link, text)

def process_text_for_links(text: str):

    def replace_with_link(mat):
        parts = mat.group(1).split("|")
        if len(parts) == 1:
            return f'<a href="{parts[0]}">{parts[0]}</a>'
        else:
            return f'<a href="{parts[0]}">{parts[1]}</a>'

    return LINK_RE.sub(replace_with_link, text)

def render_slack(text: str):
    return convert(text)

def render_thumbnail(file):
    if not file.get('thumbnail_url'):
        return f'<a href="{file["url_private"]}">{file["filetype"]}</a>'

    data_url = f"./{CACHE_DIR}/{file['thumbnail_url_hash']}"
    return f'<a href="{file["url_private"]}"><img src="{data_url}" style="max-width: 150px;" /></a>'

def render_user_img(user):
    img_url_hash = user.get('img_url_hash')
    if not img_url_hash:
        return f'<span style="display=block; max-width: 20px; max-height: 20px;background-color: #eee;" max-width="20px"></span>'

    return f'<img src="./{CACHE_DIR}/{img_url_hash}" style="max-width: 20px;" max-width="20px" />'

def img_to_data(path):
    """Convert a file (specified by a path) into a data URI."""
    if not os.path.exists(path):
        raise FileNotFoundError
    mimetype, _ = mimetypes.guess_type(path, strict=False)
    data = None

    with open(path, "rb") as fp:
        data = fp.read()

    parts = ["data:", mimetype, ";base64"]

    _charset = "utf-8"
    if isinstance(data, bytes):
        _data = data
    else:
        _data = bytes(data, _charset)
    encoded_data = base64.b64encode(_data).decode(_charset).strip()
    parts.extend([",", encoded_data])

    return "".join(parts)

def render_delta(delta: timedelta):
    parts = []
    mm, ss = divmod(delta.seconds, 60)
    hh, mm = divmod(mm, 60)
    if delta.days:
        return '%d days' % (delta.days)

    if hh:
        return '%02d hours' % (hh)

    if mm:
        return '%02d minutes' % (mm)

    if ss:
        return '%02d seconds' % (ss)
    
    return ''

@dataclass
class User:
    id: str
    name: str
    real_name_normalized: str
    img_url: Union[str, None]
    img_url_hash: Union[str, None]

    @classmethod
    def from_message(_cls, user: dict):
        img_url_hash = None
        img_url = user.get('profile', {}).get("image_192")
        if img_url:
            h = hashlib.md5(bytes(img_url, 'utf-8')).hexdigest()
            img_url_hash = f'{h}.png'

        return _cls(
            id=user["id"],
            name=user["name"],
            real_name_normalized=user.get('profile', {}).get("real_name_normalized", ""), 
            img_url=img_url,
            img_url_hash=img_url_hash,
        )

@dataclass
class Reaction:
    name: str
    count: int
    users: list[User]

    @classmethod
    def from_raw(_cls, reaction: dict, users: dict):
        return _cls(
            name=reaction['name'],
            count=reaction['count'],
            users=[users.get(x) for x in reaction.get('users', []) if users.get(x)],
        )

@dataclass
class File:
    id: str
    url_private: str
    filetype: str
    thumbnail_url: Union[str, None]
    thumbnail_url_hash: Union[str, None]
    thumbnail_width: Union[int, None]
    thumbnail_height: Union[int, None]

    @classmethod
    def from_dict(cls, data: dict):
        kwargs = {
            "id": data["id"],
            "url_private": data["url_private"],
            "filetype": data["filetype"],
        }

        if data["filetype"] == 'pdf':
            kwargs.update({
                "thumbnail_url": data.get("thumb_pdf"),
                "thumbnail_width": data.get("thumb_pdf_w"),
                "thumbnail_height": data.get("thumb_pdf_h"),
            })
        else:
            kwargs.update({
                "thumbnail_url": data.get("thumb_480"),
                "thumbnail_width": data.get("thumb_480_w"),
                "thumbnail_height": data.get("thumb_480_h"),
            })

        if kwargs['thumbnail_url']:
            h = hashlib.md5(bytes(kwargs['thumbnail_url'], 'utf-8')).hexdigest()
            e = data["filetype"]
            kwargs['thumbnail_url_hash'] = f'{h}.png'
        else:
            kwargs['thumbnail_url_hash'] = None

        return cls(**kwargs)

@dataclass
class Message:
    text: str
    user: Union[User, None]
    reactions: list[Reaction]
    datetime: datetime
    files: list[File]

    @classmethod
    def from_message(_cls, msg: dict, users: dict):
        user = msg.get('user')
        if not user:
            return None

        return _cls(
            text=process_text_for_username(msg.get('text', ''), users),
            datetime=datetime.fromtimestamp(float(msg['ts'])),
            user=msg.get('user'),
            reactions=[Reaction.from_raw(x, users) for x in msg.get('reactions', [])],
            files=[File.from_dict(x) for x in msg.get('files', [])]
        )

def persist_to_file(file_name):

    def decorator(original_func):
        cached = {}
        try:
            cached['b'] = json.load(open(file_name, 'r'))
        except (IOError, ValueError):
            cached['b'] = None

        def new_func(client: WebClient):
            if not cached['b']:
                cached['b'] = original_func(client)
                json.dump(cached['b'], open(file_name, 'w'))

            return cached['b']

        return new_func

    return decorator

@persist_to_file('_users.cache.json')
def users(client: WebClient):
    users = {}
    for page in client.users_list():
        for user in page["members"]:
            users[user['id']] = user

    return users

@persist_to_file('_emoji.cache.json')
def emojis(client: WebClient):
    response = client.emoji_list()
    emojies = response['emoji']
    for key in emojies.keys():
        val = emojies[key]
        if val.startswith('alias:'):
            emojies[key] = emojies.get(val.replace("alias:", ""))

    return emojies

def extract_channel(client: WebClient, channel_id: str, users: dict, emojis: dict):
    users = {k: User.from_message(u) for k, u in users.items()}
    for result in client.conversations_history(channel=channel_id):
        for message in result["messages"]:
            current_user = message.get('user')
            message['user'] = users.get(current_user, {"id": current_user})
            yield Message.from_message(message, users)

def download_file(url:str, local_filename:str, cookie:str):
    if os.path.isfile(local_filename):
        return local_filename

    with requests.get(url, stream=True, cookies={"d": cookie}) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                f.write(chunk)

    return local_filename

def cache_thumbs(messages: list[dict], cookie: str):
    urls_to_hash = {}
    for message in messages:
        user = message.get('user')
        if user and user.get('img_url'):
            urls_to_hash[user.get('img_url')] =  user.get('img_url_hash')

        for f in message.get('files', []):
            thumbnail_url = f.get("thumbnail_url")
            if not thumbnail_url:
                continue

            urls_to_hash[thumbnail_url] = f['thumbnail_url_hash']

    os.makedirs(CACHE_DIR, exist_ok=True)
    for key in urls_to_hash.keys():
        download_file(key, f'{CACHE_DIR}/{urls_to_hash[key]}', cookie)

def annotate_with_time(messages: list[dict]):
    start_time = None
    last_time = None
    for message in messages:
        message['datetime'] = datetime.fromisoformat(message['datetime'])

        if not start_time:
            last_time = start_time = message['datetime']

        message['delta_from_start'] = message['datetime'] - start_time
        message['delta_from_last'] = message['datetime'] - last_time

        last_time = message['datetime']

    return messages

def parse_args():
    parser = argparse.ArgumentParser(
        argument_default=None,
        description=("This is a tool developed in Python which uses the slack APIs"
                    "to extract an incident timeline from a slack channel.")
    )
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Turn on verbosity for the output files')
    parser.add_argument('--test', dest='test', action='store_true',
                        help='Test your credentials')
    parser.add_argument('--channel', dest='channel', action='store_true',
                        help='Dump a channel to stdout')
    parser.add_argument('--report', dest='report', action='store_true',
                        help='Create a report from a channel dump')
    parser.add_argument('--convert', dest='convert', action='store_true',
                        help='Convert a report to docx format')
    parser.set_defaults(test=None, channel=None, report=None, convert=None)

    return parser.parse_args()


if __name__ == '__main__':
    # Initialise the colorama module - this is used to print colourful messages - life's too dull otherwise
    args = parse_args()
    template_engine = Environment(
        loader=FileSystemLoader(os.getcwd()),
        autoescape=select_autoescape()
    )

    template_engine.globals.update(linkify=process_text_for_links)
    template_engine.globals.update(render_thumbnail=render_thumbnail)
    template_engine.globals.update(render_user_img=render_user_img)
    template_engine.globals.update(render_slack=render_slack)
    template_engine.globals.update(render_delta=render_delta)

    env = Env()
    env.read_env()  # read .env file, if it exists

    cookie = env('SLACK_COOKIE')
    token = env('SLACK_TOKEN')

    client = WebClient(
        token=token,
        headers={
            "Cookie": f'd={cookie}'
    })

    if args.test:
        api_response = client.api_test()
        if not api_response.get('ok', False):
            print("The credentials you passed in are not working.\n")
        else:
            print("The credentials are working!!!\n")

    if args.report:
        template = template_engine.get_template("report.html.jinja")
        name = env('JSON_FILE', False)
        if not name:
            print("A file must be provided to generate a report\n")
            exit(1)

        data = None
        with open(name) as fd:
            data = json.load(fd)

        cache_thumbs(data, cookie)
        data.reverse()
        data = annotate_with_time(data)
        print(template.render(messages=data))
        exit(0)

    if args.convert:
        html = env('HTML_FILE', False)
        doc = env('DOC_FILE', False)
        new_parser = HtmlToDocx()

        new_parser.parse_html_file(html, doc)

        exit(0)

    if args.channel:
        users = users(client)
        emojis = emojis(client)
        channel_id = env('CHANNEL_ID', False)
        if not channel_id:
            print("We need a channel ID to extract a channel\n")
            exit(1)

        messages = [msg for msg in extract_channel(client, channel_id, users, emojis)]
        print(json.dumps(messages, cls=EnhancedJSONEncoder))