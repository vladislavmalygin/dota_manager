"""
Migration 22: Map existing face images to players.
Also fixes dy,png → dy.png path bug.
Idempotent (skips players that already have a face set).
"""
import sqlite3

_FACE_MAP = {
    'Dy':           'players/dy.png',       # fix comma bug
    '9Class':       'players/9class.png',
    'Abed':         'players/abed.png',
    'ariel':        'players/ariel.png',
    'Ari':          'players/ari.png',
    'Armel':        'players/armel.png',
    'Batyuk':       'players/batyuk.png',
    'Benjaz':       'players/benjaz.png',
    'Bryle':        'players/bryle.png',
    'bzm':          'players/bzm.png',
    'Chalice':      'players/chalice.png',
    'Chessie':      'players/chessie.png',
    'CHIRA_JUNIOR': 'players/chira_junior.png',
    'Crystallis':   'players/crystallis.png',
    'dalul':        'players/dalul.png',
    'DarkMago':     'players/darkmago.png',
    'Davai Lama':   'players/davai_lama.png',
    'Davai':        'players/davai.png',
    'daze':         'players/daze.png',
    'dream`':       'players/dream.png',
    'Dukalis':      'players/dukalis.png',
    'Elmisho':      'players/elmisho.png',
    'Fbz':          'players/fbz.png',
    'Frank':        'players/frank.png',
    'fy':           'players/fy.png',
    'Gabbi':        'players/gabbi.png',
    'Ghost':        'players/ghost.png',
    'GH':           'players/gh.png',
    'gotthejuice':  'players/gotthejuice.png',
    'Handsken':     'players/handsken.png',
    'Inflame':      'players/inflame.png',
    'inYourdreaM':  'players/inyourdream.png',
    'Jaunuel':      'players/jaunuel.png',
    'Jikroy':       'players/jikroy.png',
    'kaori':        'players/kaori.png',
    'Kiritych':     'players/kiritych.png',
    'kpii':         'players/kpii.png',
    'Limmp':        'players/limmp.png',
    'Malady':       'players/malady.png',
    'MidOne':       'players/midone.png',
    'MikSa`':       'players/miksa.png',
    'Mirage`':      'players/mirage.png',
    'MoOz':         'players/mooz.png',
    'Natsumi':      'players/natsumi.png',
    'Nikobaby':     'players/nikobaby.png',
    'Niku':         'players/niku.png',
    'ninjaboogie':  'players/ninjaboogie.png',
    'No!ob':        'players/no_ob.png',
    'No[o]one-':    'players/noone.png',
    'NothingToSay': 'players/nothingtosay.png',
    'Noticed':      'players/noticed.png',
    'panto':        'players/panto.png',
    'payk':         'players/payk.png',
    'pma':          'players/pma.png',
    'poyoyo':       'players/poyoyo.png',
    'Pyw':          'players/pyw.png',
    'Riddys':       'players/riddys.png',
    'rincyq':       'players/rincyq.png',
    'rue':          'players/rue.png',
    'SaberLight':   'players/saberlight.png',
    'Sacred':       'players/sacred.png',
    'Saksa':        'players/saksa.png',
    'Satanic':      'players/satanic.png',
    'Sccc':         'players/sccc.png',
    'Scofield':     'players/scofield.png',
    'selfhate':     'players/selfhate.png',
    'shigetsu':     'players/shigetsu.png',
    'skem':         'players/skem.png',
    'ssnovv1':      'players/ssnovv1.png',
    'SSS':          'players/sss.png',
    'TaiLung':      'players/tailung.png',
    'Timado':       'players/timado.png',
    'TIMS':         'players/tims.png',
    'Varizh':       'players/varizh.png',
    'watson':       'players/watson.png',
    'Wits':         'players/wits.png',
    'Xakoda':       'players/xakoda.png',
    'XCJ':          'players/xcj.png',
    'xNova':        'players/xnova.png',
    'yamich':       'players/yamich.png',
    'Yamsun':       'players/yamsun.png',
    'Yopaj':        'players/yopaj.png',
    'young G':      'players/young_g.png',
}


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate22'").fetchone():
        conn.close(); return

    updated = 0
    for nick, face_path in _FACE_MAP.items():
        c.execute(
            "UPDATE players SET face=? WHERE nickname=? AND (face IS NULL OR face='' OR face=?)",
            (face_path, nick, 'players/dy,png'),
        )
        updated += c.rowcount

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate22')")
    conn.commit()
    conn.close()
    print(f"[migrate22] mapped {updated} player faces in {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
