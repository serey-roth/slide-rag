import asyncio
import json
import random
from pathlib import Path

from nicegui import ui

from src.agents.chat import ask_question
from src.learner_model import LearnerModel
from src.state import SessionState
from src.ui.components import slides_toggle
from src.utils import get_decks

_UNSEEN_TEMPLATES = [
    "Can you explain {topic}?",
    "Walk me through {topic}.",
    "What is {topic}?",
    "How does {topic} work?",
    "Give me an overview of {topic}.",
]
_SEEN_TEMPLATES = [
    "Can you give me an example of {topic}?",
    "What are the key ideas behind {topic}?",
    "How does {topic} connect to what I've studied?",
    "Can you go deeper on {topic}?",
]


def _pick_nudges(learner_model: LearnerModel, n: int = 3) -> list[str]:
    unseen, seen = [], []
    for deck in get_decks():
        for name, t in learner_model.get_deck(deck).get('topics', {}).items():
            if not t.get('progress'):
                unseen.append(name)
            else:
                seen.append(name)

    picked = (
        random.sample(unseen, min(n, len(unseen))) +
        random.sample(seen, min(max(0, n - len(unseen)), len(seen)))
    )
    random.shuffle(picked)

    prompts = []
    for topic in picked[:n]:
        template = random.choice(_UNSEEN_TEMPLATES if topic in unseen else _SEEN_TEMPLATES)
        prompts.append(template.format(topic=topic))
    return prompts



def user_bubble(container, text: str):
    with container:
        with ui.row().classes('bubble-row bubble-row-user'):
            ui.label(text).classes('bubble-user')
            ui.icon('person').classes('bubble-icon bubble-icon-user')


def assistant_bubble(container, content: str):
    with container:
        with ui.row().classes('bubble-row bubble-row-asst'):
            ui.icon('auto_awesome').classes('bubble-icon bubble-icon-asst')
            with ui.column().classes('bubble-assistant gap-2'):
                md = ui.markdown(content).classes('prose')
    try:
        ui.run_javascript(f'renderMathMarkdown({md.id}, {json.dumps(content)})')
    except RuntimeError:
        pass


async def stream_ask(
    prompt: str,
    history: list,
    on_token,
    learner_model=None,
) -> tuple[str, list[dict]]:
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    async def _run():
        try:
            return await asyncio.to_thread(
                ask_question, prompt, history,
                lambda tok: loop.call_soon_threadsafe(token_queue.put_nowait, tok),
                learner_model,
            )
        finally:
            loop.call_soon_threadsafe(token_queue.put_nowait, None)

    task = asyncio.create_task(_run())
    accumulated = ''
    while True:
        tok = await token_queue.get()
        if tok is None:
            break
        accumulated += tok
        on_token(accumulated)
    response, slides = await task
    return response, slides


def _open_decks_dialog(decks: list[str], learner_model: LearnerModel):
    preview_panels: dict = {}
    deck_cards: dict = {}
    slides_slots: dict = {}
    loaded: set[str] = set()

    def _load_slides(d: str):
        if d in loaded:
            return
        loaded.add(d)
        images_dir = Path('data/images') / d
        slide_paths = sorted(images_dir.glob('*.png')) if images_dir.exists() else []
        with slides_slots[d]:
            if not slide_paths:
                ui.label('No slides available.').classes('text-sm text-slate-400 p-4')
            else:
                with ui.column().classes('items-center gap-4 py-3 px-4 w-full'):
                    for i, path in enumerate(slide_paths, 1):
                        url = '/data/images/' + d + '/' + path.name
                        with ui.column().classes('items-center gap-1 w-full'):
                            ui.image(url).classes('w-full rounded-lg shadow-sm border border-slate-100')
                            ui.label(f'Slide {i}').classes('text-xs text-slate-400')

    def select_deck(d: str):
        for name, card in deck_cards.items():
            if name == d:
                card.classes(add='deck-list-item-active')
            else:
                card.classes(remove='deck-list-item-active')
        for name, panel in preview_panels.items():
            panel.set_visibility(name == d)
        _load_slides(d)

    with ui.dialog() as dlg:
        with ui.card().classes('decks-dialog-card'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('Decks').classes('text-sm font-semibold text-slate-700')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense color=grey')

            with ui.element('div').classes('decks-dialog-body'):
                with ui.element('div').classes('decks-dialog-list'):
                    with ui.scroll_area().classes('w-full h-full'):
                        with ui.column().classes('gap-1 w-full'):
                            for deck in decks:
                                css = 'deck-list-item' + (' deck-list-item-active' if deck == decks[0] else '')
                                with ui.element('div').classes(css).on('click', lambda _, d=deck: select_deck(d)) as card:
                                    ui.label(deck).classes('deck-item-name')
                                deck_cards[deck] = card

                with ui.element('div').classes('decks-dialog-preview'):
                    for deck in decks:
                        deck_data = learner_model.get_deck(deck)
                        summary = deck_data.get('summary', '')
                        topics = deck_data.get('topics', {})
                        with ui.element('div').classes('decks-preview-inner') as panel:
                            with ui.element('div').classes('decks-preview-header'):
                                ui.label(deck).classes('decks-preview-title')
                                if summary:
                                    ui.label(summary).classes('decks-preview-summary')
                                if topics:
                                    with ui.row().classes('flex-wrap gap-1 mt-1'):
                                        for name in list(topics.keys())[:8]:
                                            ui.label(name).classes('decks-preview-topic-chip')
                            ui.separator()
                            slides_slots[deck] = ui.element('div').classes('decks-preview-slides')
                        if deck != decks[0]:
                            panel.set_visibility(False)
                        preview_panels[deck] = panel

    _load_slides(decks[0])
    dlg.open()


def _build_chat(container, session: SessionState, learner_model: LearnerModel, on_back):
    with container:
        with ui.element('div').classes('chat-view'):
            decks = get_decks()

            with ui.element('div').classes('chat-view-header'):
                ui.button(icon='arrow_back', on_click=lambda _: on_back()).props('flat round dense')
                ui.label('Chat').classes('header-title flex-grow')
                if decks:
                    ui.button('Decks').props('flat dense color=grey').classes('header-decks-btn').on(
                        'click', lambda _: _open_decks_dialog(decks, learner_model)
                    )

            with ui.element('div').classes('chat-body'):
                with ui.element('div').classes('chat-col'):
                    with ui.scroll_area().classes('flex-grow w-full'):
                        chat_panel = ui.column().classes('chat-messages')

                    for msg in session.history:
                        if msg.get('role') == 'user':
                            user_bubble(chat_panel, msg['content'])
                        elif msg.get('role') == 'assistant':
                            assistant_bubble(chat_panel, msg['content'])

                    nudges = _pick_nudges(learner_model) if not session.history else []
                    nudge_row = None
                    if nudges:
                        nudge_row = ui.element('div').classes('nudge-row')
                        with nudge_row:
                            for prompt in nudges:
                                def make_nudge(p):
                                    def click(_=None):
                                        nudge_row.set_visibility(False)
                                        input_box.value = p
                                        input_box.run_method('focus')
                                    return click
                                ui.label(prompt).classes('nudge-chip').on('click', make_nudge(prompt))

                    with ui.element('div').classes('input-bar'):
                        with ui.element('div').classes('input-bar-inner'):
                            with ui.row().classes('input-row'):
                                input_box = (
                                    ui.input(placeholder='Ask a question...')
                                    .classes('input-text')
                                    .props('borderless dense')
                                )
                                ui.element('div').classes('input-divider')
                                send_btn = ui.button(icon='arrow_upward').props(
                                    'unelevated round color=indigo'
                                ).classes('send-btn')

    def _safe_set(el, content):
        try:
            el.set_content(content)
        except RuntimeError:
            pass

    async def send(_=None):
        text = input_box.value.strip()
        if not text:
            return
        if nudge_row:
            nudge_row.set_visibility(False)
        input_box.value = ''
        input_box.props(add='disable')

        user_bubble(chat_panel, text)

        # Build streaming bubble (cursor placeholder, slides slot)
        with chat_panel:
            with ui.row().classes('bubble-row bubble-row-asst'):
                ui.icon('auto_awesome').classes('bubble-icon bubble-icon-asst')
                with ui.column().classes('bubble-assistant gap-2'):
                    response_md = ui.markdown('▍').classes('prose')
                    slides_container = ui.element('div')

        try:
            response, slides = await stream_ask(
                text, session.history,
                lambda acc: _safe_set(response_md, acc + '▍'),
                learner_model,
            )
        except RuntimeError:
            return
        except Exception as e:
            try:
                response_md.set_content(f'Request failed: {e}')
                input_box.props(remove='disable')
            except RuntimeError:
                pass
            return

        try:
            ui.run_javascript(f'renderMathMarkdown({response_md.id}, {json.dumps(response)})')
            if slides:
                with slides_container:
                    slides_toggle(slides)
        except RuntimeError:
            pass

        session.add('user', text)
        session.add('assistant', response)
        input_box.props(remove='disable')

        if learner_model:
            from src.agents.evaluator import update_learner_model
            asyncio.create_task(asyncio.to_thread(update_learner_model, text, learner_model))

    send_btn.on('click', send)
    input_box.on('keydown.enter', send)


def chat_page():
    session = SessionState()
    learner_model = LearnerModel()

    def on_back():
        ui.navigate.to('/')

    root = ui.element('div').classes('w-full h-full')
    _build_chat(root, session, learner_model, on_back)
