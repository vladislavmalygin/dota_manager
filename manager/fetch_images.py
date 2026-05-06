#!/usr/bin/env python3
"""
Fetch player portraits and team logos from Liquipedia for Dota 2 manager game.
"""

import sqlite3
import os
import time
import re
import urllib.request
import urllib.parse
import urllib.error
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'start_database.db')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
PLAYERS_DIR = os.path.join(IMAGES_DIR, 'players')
SAVES_DIR = os.path.join(BASE_DIR, 'saves')

LIQUIPEDIA_BASE = 'https://liquipedia.net/dota2/'
HEADERS = {
    'User-Agent': 'DotaManagerGame/1.0 (personal project)',
    'Accept': 'text/html,application/xhtml+xml',
}
DELAY = 2.5  # seconds between requests

# Slug overrides for players
PLAYER_SLUG = {
    'Nisha.M': 'Nisha',
    'Ace': 'Ace',
    'Ace.RU': 'Ace',
    'Quinn.GG': 'Quinn',
    'gpk': 'Gpk',
    'miCKe': 'MiCKe',
    'tOfu': 'Tofu',
    'No[o]ne-': 'Noone-',
    'No!ob': 'No!ob',
    'Jabz2': 'Jabz',
    'Kuku2': 'Kuku',
    'NothingToSay': 'NothingToSay',
    'Kiritych': 'Kiritych',
    'Kataomi': 'Kataomi',
    'Whitemon': 'Whitemon',
    'bzm': 'Bzm',
    'Pure': 'Pure',
    'Hellscream': 'Hellscream_(Dota_2_player)',
    'Timado': 'Timado',
    'Abed': 'Abed',
    'SaberLight': 'SaberLight',
    'Fly': 'Fly',
    'GH': 'GH',
    'OmaR': 'Omar',
    'TIMS': 'TIMS',
    'skem': 'Skem',
    'Yopaj': 'Yopaj',
    'Natsumi': 'Natsumi',
    'MidOne': 'Midone',
    'BOOM': 'Boom',
    'fy': 'Fy',
    'xNova': 'XNova',
    'RAMZES666': 'Ramzes666',
    'rue': 'Rue',
    'panto': 'Panto',
    'Ari': 'Ari',
    'kaori': 'Kaori',
    'Mikoto': 'Mikoto',
    'Ws': 'Ws',
    'CCnC': 'CCnC',
    'Raven': 'Raven',
    'Gabbi': 'Gabbi',
    'March': 'March',
    'Karl': 'Karl',
    'Fng': 'Fng',
    'Solo': 'Solo',
    'ALOHADANCE': 'Alohadance',
    'Jabz': 'Jabz',
    'Kyle': 'Kyle',
    'ppd': 'PPD',
    'DJ': 'DJ_(Dota_2_player)',
    'Chalice': 'Chalice',
    'Ori': 'Ori_(player)',
    'Sccc': 'Sccc',
    'poyoyo': 'Poyoyo',
    'XCJ': 'XCJ',
    'Davai Lama': 'Davai_Lama',
    'Nikobaby': 'Nikobaby',
    'Shiro': 'Shiro_(Dota_2_player)',
    'Inflame': 'Inflame',
    'Pyw': 'Pyw',
    'xiao8': 'Xiao8',
    'QO': 'Qo',
    'Luna': 'Luna_(Dota_2_player)',
    'mp': 'Mp',
    'Nueng': 'Nueng',
    'Kennyko': 'Kennyko',
    'Armel': 'Armel',
    'Pakur': 'Pakur',
    'Kinetic': 'Kinetic_(player)',
    'Snakechuck': 'Snakechuck',
    'ninjaboogie': 'Ninjaboogie',
    'Bryle': 'Bryle',
    'Lelis': 'Lelis',
    'Yuma': 'Yuma_(player)',
    'Copy': 'Copy_(player)',
    'Gunnar': 'Gunnar',
    'KJ': 'KJ_(player)',
    'Scofield': 'Scofield',
    '4Nalog': '4Nalog',
    'Parker': 'Parker_(player)',
    'MC': 'MC_(player)',
    'Sacred': 'Sacred',
    'Benjaz': 'Benjaz',
    'TaiLung': 'TaiLung',
    'Chessie': 'Chessie',
    'Handsken': 'Handsken',
    'Limmp': 'Limmp',
    'Elmisho': 'Elmisho',
    'payk': 'Payk',
    'Lumpy': 'Lumpy_(player)',
    'Vitaly': 'Vitaly_(player)',
    'MoOz': 'MoOz',
    'selfhate': 'Selfhate',
    'young G': 'Young_G',
    'Covisnine': 'Covisnine',
    'hwoarang': 'Hwoarang_(player)',
    'VaniLLl': 'VaniLLl',
    'Fbz': 'Fbz',
    'Jaunuel': 'Jaunuel',
    'kpii': 'Kpii',
    'Kaito': 'Kaito_(player)',
    'hFnk': 'HFnk',
    'Tobias': 'Tobias_(player)',
    'Enrico': 'Enrico_(player)',
    'Bananaman': 'Bananaman_(player)',
    'Jikroy': 'Jikroy',
    'inYourdreaM': 'InYourdreaM',
    'dalul': 'Dalul',
    'Varizh': 'Varizh',
    'Super': 'Super_(player)',
    'rOtK': 'Rotk',
    'somnus': 'Somnus',
    'maybe': 'Maybe',
    'Yatoro': 'Yatoro',
    'Larl': 'Larl',
    'Collapse': 'Collapse',
    'Miposhka': 'Miposhka',
    'TORONTOTOKYO': 'Torontotokyo',
}

# Slug overrides for teams
TEAM_SLUG = {
    'BB Team': 'BetBoom_Team',
    'Xtreme Gaming': 'Xtreme_Gaming',
    'Team Spirit': 'Team_Spirit',
    'Team Liquid': 'Team_Liquid',
    'Team Falcons': 'Team_Falcons',
    'Tundra Esports': 'Tundra_Esports',
    'OG': 'OG',
    'Nigma Galaxy': 'Nigma_Galaxy',
    'Virtus.pro': 'Virtus.pro',
    'Gaimin Gladiators': 'Gaimin_Gladiators',
    'Gamin Gladiators': 'Gaimin_Gladiators',
    'Nemiga Gaming': 'Nemiga_Gaming',
    'PARIVISION': 'PARIVISION',
    'Zero Tenacity': 'Zero_Tenacity',
    'MOUZ': 'MOUZ',
    '1w Team': '1w_Team',
    'L1GA TEAM': 'L1GA_TEAM',
    'VP.Prodigy': 'VP.Prodigy',
    'Team Aster': 'Team_Aster',
    'Azure Ray': 'Azure_Ray',
    'Natus Vincere': 'Natus_Vincere',
    'T1': 'T1',
    'Fnatic': 'Fnatic',
    'Evil Geniuses': 'Evil_Geniuses',
    'Blacklist International': 'Blacklist_International',
    'Entity': 'Entity',
    'Thunder Awaken': 'Thunder_Awaken',
    'Alliance': 'Alliance',
    'Execration': 'Execration',
    'REKONIX': 'REKONIX',
    'Rejects': 'Rejects',
    'nouns': 'nouns',
    'Heroic': 'Heroic',
    'Beastcoast': 'Beastcoast',
    'Aurora': 'Aurora',
}

try:
    from PIL import Image
    import io
    HAS_PIL = True
    print("PIL available - will resize images to max 200x200")
except ImportError:
    HAS_PIL = False
    print("PIL not available - saving images as-is")


def get_player_slug(nickname):
    if nickname in PLAYER_SLUG:
        return PLAYER_SLUG[nickname]
    return nickname


def get_team_slug(team_name):
    if team_name in TEAM_SLUG:
        return TEAM_SLUG[team_name]
    return team_name.replace(' ', '_')


def fetch_page(slug):
    url = LIQUIPEDIA_BASE + urllib.parse.quote(slug, safe='._-()/')
    print(f"  Fetching page: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}")
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def extract_image_url_from_infobox(html):
    """
    Extract the portrait/logo image from a Liquipedia infobox.
    Looks for <div class="infobox-image"> or <div class="infobox-center">
    containing an <img> tag, or infobox-icon.
    Falls back to first player/team portrait img in the page.
    """
    # Try infobox image area first
    patterns = [
        # infobox-image-icon or infobox-image
        r'<div[^>]+class="[^"]*infobox-image[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
        r'<div[^>]+class="[^"]*infobox-center[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
        # wikitable with player portrait
        r'<div[^>]+class="[^"]*floatnone[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            src = m.group(1)
            if '/commons/images/' in src or '/thumb/' in src:
                return src

    # Broader: find first img with /commons/images/ in src inside infobox area
    infobox_m = re.search(r'<div[^>]+class="[^"]*infobox[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL | re.IGNORECASE)
    if infobox_m:
        infobox_html = infobox_m.group(1)
        img_m = re.search(r'<img[^>]+src="([^"]+/commons/images/[^"]+)"', infobox_html, re.IGNORECASE)
        if img_m:
            return img_m.group(1)

    # Last resort: find any img with commons/images containing typical portrait patterns
    all_imgs = re.findall(r'<img[^>]+src="([^"]+/commons/images/[^"]+)"[^>]*>', html, re.IGNORECASE)
    for src in all_imgs:
        # Prefer player portraits (not flags, not small icons)
        low = src.lower()
        if any(x in low for x in ['flag', 'logo', 'icon', 'blank']):
            continue
        if 'thumb' in low or re.search(r'/[a-f0-9]/[a-f0-9]{2}/', low):
            return src

    # For teams, allow logo images
    for src in all_imgs:
        low = src.lower()
        if 'flag' in low:
            continue
        return src

    return None


def thumb_to_full(src):
    """Convert /thumb/ URL to full-size image URL."""
    # /commons/images/thumb/a/ab/File.png/300px-File.png -> /commons/images/a/ab/File.png
    m = re.match(r'(.*?/commons/images)/thumb(/[a-f0-9]/[a-f0-9]{2}/[^/]+)\.[a-z]+/\d+px-.*', src, re.IGNORECASE)
    if m:
        base = m.group(1)
        path = m.group(2)
        # Reconstruct extension from original filename in path
        fname = path.rsplit('/', 1)[-1]
        return base + path + '.' + src.rsplit('.', 1)[-1].split('/')[0]

    # Try simpler pattern: strip /thumb/ and trailing /NNNpx-filename part
    if '/thumb/' in src:
        # Remove /thumb from path
        no_thumb = src.replace('/thumb/', '/', 1)
        # Remove trailing /NNNpx-... component
        no_thumb = re.sub(r'/\d+px-[^/]+$', '', no_thumb)
        return no_thumb
    return src


def make_full_url(src):
    """Make a full URL from a possibly-relative src."""
    if src.startswith('http'):
        return src
    if src.startswith('//'):
        return 'https:' + src
    return 'https://liquipedia.net' + src


def download_image(url, save_path):
    """Download image and save, optionally resizing."""
    print(f"  Downloading: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} downloading image")
        return False
    except Exception as e:
        print(f"  Error downloading: {e}")
        return False

    if len(data) < 500:
        print(f"  Image too small ({len(data)} bytes), skipping")
        return False

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if HAS_PIL:
        try:
            img = Image.open(io.BytesIO(data))
            img = img.convert('RGBA')
            img.thumbnail((200, 200), Image.LANCZOS)
            img.save(save_path, 'PNG')
            print(f"  Saved (resized) to {save_path}")
            return True
        except Exception as e:
            print(f"  PIL error: {e}, saving raw")

    with open(save_path, 'wb') as f:
        f.write(data)
    print(f"  Saved to {save_path}")
    return True


def update_db(db_path, updates_players, updates_teams):
    """Apply face/logo updates to a database file."""
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for player_id, face_val in updates_players.items():
            cur.execute("UPDATE Players SET face=? WHERE id=?", (face_val, player_id))
        for team_id, logo_val in updates_teams.items():
            cur.execute("UPDATE teams SET logo=? WHERE id=?", (logo_val, team_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  DB update error for {db_path}: {e}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get players missing faces, ordered by team rating desc
    cur.execute("""
        SELECT p.id, p.nickname, p.team_id, t.rating
        FROM Players p
        JOIN teams t ON p.team_id = t.id
        WHERE p.team_id != 0 AND (p.face IS NULL OR p.face = '')
        ORDER BY t.rating DESC, p.id
    """)
    players_todo = cur.fetchall()

    # Get teams missing logos
    cur.execute("""
        SELECT id, name FROM teams
        WHERE id != 0 AND (logo IS NULL OR logo = '')
        ORDER BY rating DESC
    """)
    teams_todo = cur.fetchall()
    conn.close()

    print(f"\nPlayers needing faces: {len(players_todo)}")
    print(f"Teams needing logos: {len(teams_todo)}")

    player_updates = {}  # id -> face path
    team_updates = {}    # id -> logo filename

    downloaded_players = 0
    downloaded_teams = 0
    skipped_players = 0
    skipped_teams = 0

    # --- Process players ---
    print("\n" + "="*60)
    print("PROCESSING PLAYERS")
    print("="*60)

    for player_id, nickname, team_id, rating in players_todo:
        print(f"\n[Player] {nickname} (id={player_id}, team_id={team_id}, rating={rating})")
        slug = get_player_slug(nickname)
        print(f"  Slug: {slug}")

        time.sleep(DELAY)
        html = fetch_page(slug)
        if not html:
            print(f"  SKIP: Could not fetch page")
            skipped_players += 1
            continue

        src = extract_image_url_from_infobox(html)
        if not src:
            print(f"  SKIP: No image found in page")
            skipped_players += 1
            continue

        print(f"  Raw src: {src}")
        full_src = thumb_to_full(src)
        full_url = make_full_url(full_src)
        print(f"  Full URL: {full_url}")

        # Save path: images/players/{nickname_lower}.png
        safe_nick = re.sub(r'[^a-zA-Z0-9_\-]', '_', nickname).lower()
        # Use standard name from existing convention where possible
        nick_lower = nickname.lower()
        save_filename = f"{safe_nick}.png"
        save_path = os.path.join(PLAYERS_DIR, save_filename)
        face_val = f"players/{save_filename}"

        time.sleep(DELAY)
        ok = download_image(full_url, save_path)
        if ok:
            player_updates[player_id] = face_val
            downloaded_players += 1
        else:
            skipped_players += 1

    # --- Process teams ---
    print("\n" + "="*60)
    print("PROCESSING TEAMS")
    print("="*60)

    for team_id, team_name in teams_todo:
        print(f"\n[Team] {team_name} (id={team_id})")
        slug = get_team_slug(team_name)
        print(f"  Slug: {slug}")

        time.sleep(DELAY)
        html = fetch_page(slug)
        if not html:
            print(f"  SKIP: Could not fetch page")
            skipped_teams += 1
            continue

        # For teams, look for logo image - try infobox-image first, then any logo
        src = None

        # Team infobox logo patterns
        logo_patterns = [
            r'<div[^>]+class="[^"]*infobox-image[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
            r'<div[^>]+class="[^"]*infobox-center[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
            r'<div[^>]+class="[^"]*team-template-image[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
        ]
        for pat in logo_patterns:
            m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
            if m:
                candidate = m.group(1)
                if '/commons/images/' in candidate or '/thumb/' in candidate:
                    src = candidate
                    break

        if not src:
            # Broader search in infobox area
            all_imgs = re.findall(r'<img[^>]+src="([^"]+/commons/images/[^"]+)"[^>]*>', html, re.IGNORECASE)
            for candidate in all_imgs:
                low = candidate.lower()
                if 'flag' in low:
                    continue
                src = candidate
                break

        if not src:
            print(f"  SKIP: No image found for team")
            skipped_teams += 1
            continue

        print(f"  Raw src: {src}")
        full_src = thumb_to_full(src)
        full_url = make_full_url(full_src)
        print(f"  Full URL: {full_url}")

        # Save path: images/{TeamName}_logo.png
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', team_name)
        # Clean up multiple underscores
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        logo_filename = f"{safe_name}_logo.png"
        save_path = os.path.join(IMAGES_DIR, logo_filename)

        time.sleep(DELAY)
        ok = download_image(full_url, save_path)
        if ok:
            team_updates[team_id] = logo_filename
            downloaded_teams += 1
        else:
            skipped_teams += 1

    # --- Update databases ---
    print("\n" + "="*60)
    print("UPDATING DATABASES")
    print("="*60)

    print(f"\nUpdating main DB: {DB_PATH}")
    update_db(DB_PATH, player_updates, team_updates)

    save_files = glob.glob(os.path.join(SAVES_DIR, '*.db'))
    for save_path in save_files:
        print(f"Updating save: {save_path}")
        update_db(save_path, player_updates, team_updates)

    # --- Summary ---
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Players downloaded: {downloaded_players} / {len(players_todo)}")
    print(f"Players skipped:    {skipped_players}")
    print(f"Teams downloaded:   {downloaded_teams} / {len(teams_todo)}")
    print(f"Teams skipped:      {skipped_teams}")
    print(f"Total images:       {downloaded_players + downloaded_teams}")
    print(f"DBs updated:        1 main + {len(save_files)} saves")


if __name__ == '__main__':
    main()
