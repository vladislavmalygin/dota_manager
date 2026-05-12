import sys
import os

if getattr(sys, 'frozen', False):
    # onedir: assets are in sys._MEIPASS (_internal/), exe one level up.
    # cd into _internal so relative paths (images/, start_database.db) resolve.
    os.chdir(sys._MEIPASS)
    # saves/ next to the exe (user-writable, survives updates)
    saves_dir = os.path.join(os.path.dirname(sys.executable), 'saves')
    os.makedirs(saves_dir, exist_ok=True)
    # patch saves/ to point there via symlink inside _internal
    saves_link = os.path.join(sys._MEIPASS, 'saves')
    if not os.path.exists(saves_link):
        os.symlink(saves_dir, saves_link)

from main_menu import Dota_Manager

if __name__ == '__main__':
    Dota_Manager().run()
