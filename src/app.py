import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from nicegui import app, ui

app.add_static_files('/data', str(Path('data').resolve()))

from src import styles

styles.apply()

from src.ui.chat import chat_page
from src.ui.home import index
from src.ui.quiz import quiz_page

ui.page('/')(index)
ui.page('/chat')(chat_page)
ui.page('/quiz')(quiz_page)

_storage_secret = os.environ.get('NICEGUI_STORAGE_SECRET', 'dev-only-set-NICEGUI_STORAGE_SECRET-in-production')
ui.run(title='Lecture Assistant', port=8080, reload=True, storage_secret=_storage_secret)
