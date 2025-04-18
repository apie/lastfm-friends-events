#!/usr/bin/env python3
# Scrape lastfm user event page
# By Apie
# 2024-01-25
import typer
from requests_html import HTMLSession
from lxml import etree

from os import path
from pathlib import Path
from sys import argv
from datetime import timedelta, datetime
from typing import List, Set
import pytz

timezone = "Europe/Amsterdam"

import requests_cache

from requests_cache import CacheMixin, install_cache

from requests_html import HTMLSession


class CachedHTMLSession(CacheMixin, HTMLSession):
    """Session with features from both CachedSession and HTMLSession"""


urls_expire_after = {
    "*": 60 * 60 * 24 * 5,
    # cache friends longer than events
    # cache if friend is still scrobbling/active
}
session = CachedHTMLSession(
    "lfm-friends-events-cache", urls_expire_after=urls_expire_after
)


def get_events(username: str):
    import time
    time.sleep(3)
    # No year means upcoming events
    url = f"https://www.last.fm/user/{username}/events"
    r = session.get(url, headers={'User-Agent': 'Firefox'})
    r.raise_for_status()
    try:
        events = r.html.find("tr.events-list-item")
    except e:
        print(e)
        return
    for event in events:
        datetimestr = event.find("time", first=True).attrs.get("datetime")
        link = "https://www.last.fm" + event.find(
            "a.events-list-cover-link", first=True
        ).attrs.get("href")
        title = event.find(".events-list-item-event--title", first=True).text
        lineup = event.find(
            ".events-list-item-event--lineup", first=True
        ).text  # Does not include main act
        location = event.find(".events-list-item-venue", first=True).text
        date_obj = datetime.fromisoformat(datetimestr).date()
        yield date_obj, link, title, lineup, location

def get_user_list(url: str) -> Set[str]:
    # TODO pagination
    r = session.get(url)
    r.raise_for_status()
    following = set()
    for followinger in r.html.find("li.user-list-item.link-block"):
        name = followinger.find(".user-list-name", first=True).text
        print(name)
        following.add(name)
    # raise NotImplementedError()
    print(following)
    return following

def get_followers(username: str) -> Set[str]:
    url = f"https://www.last.fm/user/{username}/followers"
    return get_user_list(url)

def get_following(username: str) -> Set[str]:
    url = f"https://www.last.fm/user/{username}/following"
    return get_user_list(url)

def get_friends(username: str) -> List[str]:
    # Friends = people who are in both your 'followers' and 'following'
    # return ['onemoregirl']
    following = get_following(username)
    followers = get_followers(username)
    # print(followers.intersection(following))
    # import pdb; pdb.set_trace()
    return followers.intersection(following)


def print_events(username: str):
    for friend in get_friends(username):
        print(friend)
        # TODO if friend is still active
        for i, event in enumerate(get_events(friend)):
            if not event:
                continue
            if i > 2:
                continue
            date_obj, link, title, lineup, location = event
            print(f"- {date_obj=} {link=} {title=} {lineup=} {location=}")
        print("")


if __name__ == "__main__":
    typer.run(print_events)
