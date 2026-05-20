#!/usr/bin/env python3
"""
Download Dota 2 hero portrait images from Valve CDN.
Run from manager/ directory: python fetch_hero_images.py
"""
import os
import time
import urllib.request

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR  = os.path.join(BASE_DIR, 'hero_images')
CDN_BASE    = 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes'
DELAY       = 0.4   # seconds between requests

os.makedirs(IMAGES_DIR, exist_ok=True)

from logic.heroes import HERO_SLUG_MAP

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
}


def download_hero(slug):
    url      = f'{CDN_BASE}/{slug}_full.png'
    out_path = os.path.join(IMAGES_DIR, f'{slug}_full.png')
    if os.path.exists(out_path):
        return True, 'skip'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(out_path, 'wb') as f:
            f.write(data)
        return True, 'ok'
    except Exception as e:
        return False, str(e)


def main():
    slugs = sorted(set(HERO_SLUG_MAP.values()))
    ok = skip = fail = 0
    for i, slug in enumerate(slugs, 1):
        success, status = download_hero(slug)
        if status == 'skip':
            skip += 1
            print(f'  [{i}/{len(slugs)}] skip  {slug}')
        elif success:
            ok += 1
            print(f'  [{i}/{len(slugs)}] OK    {slug}')
            time.sleep(DELAY)
        else:
            fail += 1
            print(f'  [{i}/{len(slugs)}] FAIL  {slug}: {status}')
    print(f'\nDone: {ok} downloaded, {skip} skipped, {fail} failed')
    print(f'Images saved to: {IMAGES_DIR}')


if __name__ == '__main__':
    main()
