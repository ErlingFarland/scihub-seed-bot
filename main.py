import json
import os
import random
import time
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from threading import RLock

import requests
from torrentool.api import Torrent
from bs4 import BeautifulSoup as bs
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Updater

torrent_root = Path('torrents')
hash_root = Path('cache')
torrent_root.mkdir(exist_ok=True)
hash_root.mkdir(exist_ok=True)
cache_ts = 0
cache_data = None


class Seed(NamedTuple):
    url: str
    size: str
    seeders: int
    peers: int


def load_config():
    with open('config.json') as f:
        return json.load(f)


bot_config = load_config()
BOT_TOKEN = bot_config['token']
CACHE_TIME = bot_config['cache_time'] * 60


def poll_torrents():
    url = 'https://phillm.net/torrent-health-frontend/stats-filtered-table.php?propname[]=seeders&comp[]=%3C&value[]=50&propname[]=type&comp[]===&value[]=scimag'
    res = requests.get(url)
    html = bs(res.text, 'html.parser')
    for tr in html.find_all('tr'):
        children = list(tr.find_all('td'))
        url = children[2].string
        size = children[3].string
        seeders = children[4].string
        peers = children[7].string
        yield Seed(
            url=url,
            size=size,
            seeders=int(seeders),
            peers=int(peers)
        )


def url_to_filename(url):
    name = os.path.basename(url)
    fp = torrent_root / name
    return fp


def download_torrent(url):
    fp = url_to_filename(url)
    if not fp.exists():
        res = requests.get(url)
        with open(fp, 'wb') as f:
            f.write(res.content)
    return fp


def url_to_magnet(url):
    fp = download_torrent(url)
    torrent = Torrent.from_file(fp)
    return torrent.magnet_link


@lru_cache(128)
def url_to_magnet_cached(url):
    name = os.path.basename(url)
    fp = hash_root / name
    if fp.exists():
        return fp.read_text('utf-8')
    else:
        magnet = url_to_magnet(url)
        fp.write_text(magnet, 'utf-8')
        return magnet


def poll_latest_seeds():
    seeds = list(poll_torrents())
    min_seeders = min(s.seeders for s in seeds)
    return [
        s
        for s in seeds
        if s.seeders == min_seeders
    ]


def poll_torrents_with_cache():
    ts = time.time()
    global cache_ts, cache_data
    if ts - cache_ts > CACHE_TIME or not cache_data:
        cache_data = poll_latest_seeds()
        cache_ts = ts
    return cache_data


poll_lock = RLock()


def handle_command(update: Update, ctx: CallbackContext):
    if time.time() - cache_ts > CACHE_TIME:
        update.message.reply_text('????????????????????????????????????\nCaching. It may take a few seconds.')
    with poll_lock:
        seeds = poll_torrents_with_cache()
    if not seeds:
        update.message.reply_text('????????????: ??????????????????, ?????????????????????\n Error: Empty torrent list. Something is wrong.')
        return
    seed = random.choice(seeds)
    magnet = url_to_magnet_cached(seed.url)
    text = f'Seeders: {seed.seeders}\nSize: {seed.size}\nTorrent: [{seed.url}]({seed.url})\nMagnet????: `{magnet}` (????????????/Click To Copy)'
    update.message.reply_text(text, parse_mode='markdown')


def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("seed", handle_command))
    updater.start_polling()
    print("Bot started.")
    updater.idle()


if __name__ == '__main__':
    main()
