#!/usr/bin/env python3
# Scrape lastfm user event page
# By Apie
# 2025-04-18

import time
import random
import logging
from os import path
from pathlib import Path
from sys import argv
from datetime import timedelta, datetime
from typing import List, Set
from urllib.parse import urljoin, urlparse

import pytz
import typer
import requests_cache
from lxml import etree
from requests_html import HTML, HTMLSession


logger = logging.getLogger(__name__)

ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24
ONE_YEAR = ONE_DAY * 365
urls_expire_after = {
    "*": ONE_DAY * 5,
    # cache if friend is still scrobbling/active
    "https://www.last.fm/user/*/listening-report/year": ONE_YEAR * 99,
}
session = requests_cache.CachedSession(
    "lfm-friends-events-cache",
    urls_expire_after=urls_expire_after,
)


def user_is_active(username: str) -> bool:
    url = f"https://www.last.fm/user/{username}/listening-report/year"
    logger.debug(f"getting {url}")
    r = session.get(
        url, headers={"User-Agent": "Firefox", "Cookie": "hallo=1"}
    )  # Force cookie header so we have idential cookies every time and the request can be cached.
    r.raise_for_status()
    logger.debug(f"{r.from_cache=}")
    if not r.from_cache:
        noise = random.randint(1, 100)
        sleeping = random.randint(0, 3) + (noise / 100)
        logger.debug(f"{sleeping=}")
        # Give the last.fm site some rest and prevent rate limiting
        time.sleep(sleeping)
    html = HTML(html=r.content)
    text = html.search("Nothing to report")
    if not text:
        return True


def get_events(username: str):
    # No year means upcoming events
    url = f"https://www.last.fm/user/{username}/events"
    logger.debug(f"getting {url}")
    r = session.get(
        url, headers={"User-Agent": "Firefox", "Cookie": "hallo=1"}
    )  # Force cookie header so we have idential cookies every time and the request can be cached.
    r.raise_for_status()
    logger.debug(f"{r.from_cache=}")
    if not r.from_cache:
        noise = random.randint(1, 100)
        sleeping = random.randint(0, 3) + (noise / 100)
        logger.debug(f"{sleeping=}")
        # Give the last.fm site some rest and prevent rate limiting
        time.sleep(sleeping)
    html = HTML(html=r.content)
    try:
        events = html.find("tr.events-list-item")
    except e:
        return print(e)
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
    following = set()
    logger.debug(f"getting {url}")
    r = session.get(
        url, headers={"User-Agent": "Firefox", "Cookie": "hallo=1"}
    )  # Force cookie header so we have idential cookies every time and the request can be cached.
    r.raise_for_status()
    logger.debug(f"{r.from_cache=}")
    html = HTML(html=r.content)
    for followinger in html.find("li.user-list-item.link-block"):
        name = followinger.find(".user-list-name", first=True).text
        following.add(name)
    next_elem = html.find("li.pagination-next a", first=True)
    if next_elem:
        next_page = next_elem.attrs.get("href")
        base_url = urljoin(url, urlparse(url).path)
        new_followers = get_user_list(base_url + next_page)
        following.update(new_followers)
    return following


def get_followers(username: str) -> Set[str]:
    url = f"https://www.last.fm/user/{username}/followers"
    return get_user_list(url)


def get_following(username: str) -> Set[str]:
    url = f"https://www.last.fm/user/{username}/following"
    return get_user_list(url)


def get_friends(username: str, friends_only: bool) -> List[str]:
    # Friends = people who are in both your 'followers' and 'following'
    following = get_following(username)
    followers = get_followers(username)
    if friends_only:
        # Return only people that are in both sets. You follow them and they follow you back.
        return followers.intersection(following)
    # Return both followers and following
    return followers.union(following)


def print_events(username: str, friends_only: bool = False, debug: bool = False):
    if debug:
        logging.basicConfig(level="DEBUG")
    for friend in sorted(get_friends(username, friends_only), key=lambda x: x.lower()):
        if not user_is_active(friend):
            logger.debug(f"Skipping inactive user {friend}")
            continue
        for i, event in enumerate(get_events(friend)):
            if not event:
                continue
            if i > 2:
                continue  # Only print first three events friend is going to.
            date_obj, link, title, lineup, location = event
            print(f"{friend}: {title} on {date_obj} {link=}")


if __name__ == "__main__":
    typer.run(print_events)
