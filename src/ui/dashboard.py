import asyncio
from datetime import datetime, timezone
from pathlib import Path

from nicegui import ui

from src.learner_model import LearnerModel
from src.utils import DECKS_DIR, get_decks


def _open_upload_dialog(on_file_upload):
    with ui.dialog() as dlg:
        with ui.card().classes('upload-card'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('Upload').classes('text-sm font-semibold text-slate-700')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense color=grey')

            async def on_upload(e):
                dlg.close()
                await on_file_upload(e)

            (
                ui.upload(on_upload=on_upload, auto_upload=True)
                .props('accept=".pdf" max-files="1"')
                .classes('upload-hidden')
            )
            with ui.element('div').classes('upload-dropzone').on('click', lambda _: ui.run_javascript(
                'document.querySelector(".upload-hidden input[type=file]").click()'
            )):
                ui.icon('cloud_upload').classes('upload-drop-icon')
                ui.label('Drop a PDF here or click to browse').classes('upload-drop-title')
    dlg.open()
    
    
def _open_deck_preview(deck: str):
    images_dir = Path('data/images') / deck
    slide_paths = sorted(images_dir.glob('*.png')) if images_dir.exists() else []

    with ui.dialog().props('maximized') as dlg:
        with ui.column().classes('w-full h-full bg-slate-50'):
            with ui.row().classes('items-center gap-2 px-4 py-2 bg-white border-b border-slate-100 flex-shrink-0'):
                ui.button(icon='arrow_back', on_click=dlg.close).props('flat round dense')
                ui.label(deck).classes('text-sm font-semibold text-slate-700')
                if slide_paths:
                    ui.label(f'{len(slide_paths)} slides').classes('text-xs text-slate-400 ml-1')
            with ui.scroll_area().classes('flex-grow w-full'):
                if not slide_paths:
                    with ui.column().classes('items-center justify-center w-full h-full gap-2 p-8'):
                        ui.label('No slides available.').classes('text-sm text-slate-400')
                        ui.label('This deck may not have been ingested yet.').classes('text-xs text-slate-400')
                else:
                    with ui.column().classes('items-center gap-4 py-6 px-4 w-full'):
                        for i, path in enumerate(slide_paths, 1):
                            url = '/data/images/' + deck + '/' + path.name
                            with ui.column().classes('items-center gap-1 w-full max-w-3xl'):
                                ui.image(url).classes('w-full rounded shadow-sm border border-slate-200')
                                ui.label(f'Slide {i}').classes('text-xs text-slate-400')
    dlg.open()



def build_dashboard(container, learner_model: LearnerModel):
    async def handle_upload(e):
        DECKS_DIR.mkdir(parents=True, exist_ok=True)
        dest = DECKS_DIR / e.file.name
        dest.write_bytes(await e.file.read())
        notify = ui.notification(f'Ingesting {e.file.name}…', spinner=True, timeout=None, close_button=False, position='top')
        await asyncio.sleep(0)
        try:
            from src.ingest import ingest
            await asyncio.to_thread(ingest, str(dest))
            learner_model._data = learner_model._load()
            cta_row.refresh()
            deck_list.refresh()
            notify.dismiss()
            ui.notify(f'{dest.stem} ingested!', type='positive')
        except Exception as ex:
            notify.dismiss()
            ui.notify(f'Ingest failed: {ex}', type='negative')

    with container:
        with ui.element('div').classes('dashboard'):
            with ui.element('div').classes('dash-header'):
                ui.label('Lecture Assistant').classes('header-title')

            with ui.element('div').classes('dash-content'):
                @ui.refreshable
                def cta_row():
                    has_decks = bool(get_decks())
                    with ui.row().classes('cta-row'):
                        chat_cls = 'cta-card' + ('' if has_decks else ' cta-card-disabled')
                        with ui.element('div').classes(chat_cls).on('click', lambda _: ui.navigate.to('/chat') if get_decks() else None):
                            ui.label('Chat').classes('cta-title')
                            ui.label('Ask questions about your lecture slides').classes('cta-subtitle')
                        quiz_cls = 'cta-card' + ('' if has_decks else ' cta-card-disabled')
                        with ui.element('div').classes(quiz_cls).on('click', lambda _: ui.navigate.to('/quiz') if get_decks() else None):
                            ui.label('Quiz').classes('cta-title')
                            ui.label('Test yourself on topics from your lectures').classes('cta-subtitle')

                cta_row()

                with ui.element('div').classes('dash-section'):
                    @ui.refreshable
                    def deck_list():
                        decks = get_decks()
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label('Decks').classes('section-heading')
                                if decks:
                                    ui.label(str(len(decks))).classes('section-count')
                            if decks:
                                ui.label('Upload').classes('view-all-link').on('click', lambda _: _open_upload_dialog(handle_upload))
                        if not decks:
                            with ui.element('div').classes('deck-empty-state'):
                                ui.label('No decks uploaded yet.').classes('deck-empty text-center w-full')
                                ui.button('Upload', on_click=lambda: _open_upload_dialog(handle_upload)).props('unelevated color=indigo').classes('mt-2 self-center')
                            return
                        for deck in decks:
                            deck_data = learner_model.get_deck(deck)
                            topics = deck_data.get('topics', {})
                            summary = deck_data.get('summary', '')
                            last_seen = max(
                                (t.get('last_seen') or '' for t in topics.values()),
                                default=''
                            )
                            with ui.element('div').classes('deck-list-item').on('click', lambda _, d=deck: _open_deck_preview(d)):
                                with ui.row().classes('items-center gap-2 w-full'):
                                    ui.label(deck).classes('deck-item-name flex-grow')
                                    if last_seen:
                                        delta = datetime.now(timezone.utc) - datetime.fromisoformat(last_seen)
                                        days = delta.days
                                        ui.label('today' if days == 0 else f'{days}d ago').classes('deck-item-age')
                                if summary:
                                    ui.label(summary).classes('deck-item-summary')

                    deck_list()
