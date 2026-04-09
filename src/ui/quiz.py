import asyncio
import re

from nicegui import ui
from src.agents.evaluator import update_learner_model_from_quiz

from src.agents.quiz import DEFAULT_NUM_QUESTIONS, Question, Quiz, generate_quiz
from src.learner_model import LearnerModel
from src.ui.components import slides_toggle
from src.utils import get_decks


def _render_quiz_progress(current: int, total: int):
    with ui.row().classes('step-dots'):
        for i in range(total):
            ui.element('div').classes('step-dot' + (' step-dot-active' if i < current else ''))


def _render_mcq(question: str, options: list[str], correct_idx: int, on_submit, slides=None):
    selected = {'value': None, 'locked': False}
    option_els = []

    ui.label(question).classes('question-text')

    if slides and re.search(r'\bslide\s*\d+\b', question, re.IGNORECASE):
        slides_toggle(slides)

    with ui.column().classes('gap-2 w-full mt-2'):
        for i, opt in enumerate(options):
            with ui.row().classes('option-row items-start gap-3 w-full flex-nowrap') as row:
                ui.label(chr(65 + i)).classes('option-letter')
                ui.label(opt).classes('option-text flex-1')
            option_els.append(row)

            def make_select(idx):
                def select(_=None):
                    if selected['locked']:
                        return
                    selected['value'] = idx
                    for j, el in enumerate(option_els):
                        if j == idx:
                            el.classes(add='option-selected')
                        else:
                            el.classes(remove='option-selected')
                return select

            row.on('click', make_select(i))

    action_area = ui.column().classes('gap-2 w-full')
    submit_btn = ui.button('Submit').props('unelevated color=indigo').classes('w-full mt-2')

    def submit(_=None):
        if selected['value'] is None:
            with action_area:
                ui.label('Select an answer first.').classes('validation-msg')
            return
        selected['locked'] = True
        submit_btn.set_visibility(False)
        val = selected['value']
        correct = val == correct_idx
        for i, el in enumerate(option_els):
            el.classes(remove='option-selected')
            el.classes(add='option-locked')
            if i == val and correct:
                el.classes(add='option-result-correct')
            elif i == val:
                el.classes(add='option-result-wrong')
            elif i == correct_idx:
                el.classes(add='option-result-correct')
        on_submit(val, action_area)

    submit_btn.on_click(submit)


def _render_quiz_summary(quiz_state: dict, total: int, on_restart, on_close):
    score = quiz_state['score']
    pct = round(score / total * 100)
    passed = pct >= 60
    missed = [r for r in quiz_state['results'] if not r['correct']]

    if pct >= 80:
        tier_text = 'Strong grasp of the material'
    elif pct >= 50:
        tier_text = 'Partial understanding — keep practicing'
    else:
        tier_text = 'Needs more review'

    with ui.scroll_area().classes('flex-grow w-full'):
        with ui.column().classes('quiz-complete w-full'):
            with ui.column().classes('quiz-complete-summary'):
                icon = 'check_circle' if passed else 'cancel'
                icon_cls = 'quiz-complete-icon-pass' if passed else 'quiz-complete-icon-fail'
                ui.icon(icon).classes(f'quiz-complete-icon {icon_cls}')
                ui.label(f'{score} / {total}').classes('quiz-score')
                ui.label(tier_text).classes('score-tier-text')

            ui.separator().classes('w-full my-2')
            if missed:
                review_label = 'Review' if len(missed) == total else f'{len(missed)} to review'
                ui.label(review_label).classes('quiz-review-heading')
                with ui.column().classes('gap-3 w-full'):
                    for r in missed:
                        q = r['q']
                        with ui.element('div').classes('quiz-review-card'):
                            ui.label(q.prompt).classes('question-text quiz-review-question')
                            with ui.column().classes('gap-1 mt-2'):
                                with ui.row().classes('items-start gap-2'):
                                    ui.icon('cancel').classes('result-icon-wrong text-sm mt-0.5')
                                    ui.label(q.options[r['selected']]).classes('result-text-wrong text-sm')
                                with ui.row().classes('items-start gap-2'):
                                    ui.icon('check_circle').classes('result-icon-correct text-sm mt-0.5')
                                    ui.label(q.options[q.answer]).classes('result-text-correct text-sm')
            else:
                ui.label('Perfect score — no mistakes to review.').classes('text-sm text-slate-400 text-center w-full')

            with ui.row().classes('quiz-complete-actions'):
                ui.button('Try again', on_click=on_restart).props('unelevated color=indigo')
                ui.button('Close', on_click=on_close).props('flat color=grey')


def open_quiz_overlay(quiz: Quiz, learner_model=None, on_close=None):
    quiz_state = {'idx': 0, 'score': 0, 'results': []}

    with ui.dialog().props('maximized persistent') as dlg:
        with ui.element('div').classes('quiz-overlay'):
            with ui.element('div').classes('quiz-overlay-header'):
                with ui.column().classes('gap-0'):
                    ui.label('Quiz').classes('quiz-label')
                    ui.label(', '.join(t.title() for t in quiz.topics)).classes('quiz-topic')
                def _close():
                    dlg.close()
                    if on_close:
                        on_close()
                ui.button(icon='close', on_click=lambda _: _close()).props('flat round dense color=grey')
            content = ui.element('div').classes('quiz-overlay-content')

    def load_question():
        content.clear()
        idx, total = quiz_state['idx'], len(quiz.questions)

        with content:
            if idx >= total:
                if learner_model:
                    asyncio.ensure_future(asyncio.to_thread(
                        update_learner_model_from_quiz, quiz, quiz_state['results'], learner_model
                    ))
                def restart(_=None):
                    quiz_state.update({'idx': 0, 'score': 0, 'results': []})
                    load_question()
                _render_quiz_summary(quiz_state, total, on_restart=restart, on_close=_close)
                return

            q = quiz.questions[idx]
            with ui.column().classes('quiz-progress'):
                _render_quiz_progress(idx + 1, total)
                ui.label(f'{idx + 1} of {total}').classes('progress-count')
            ui.separator().classes('flex-shrink-0')

            with ui.scroll_area().classes('flex-grow w-full'):
                with ui.column().classes('quiz-body'):
                    with ui.column().classes('gap-3 w-full'):
                        _render_mcq(q.prompt, q.options, q.answer,
                             on_submit=lambda val, area: on_answer(val, area, q, idx, total),
                             slides=q.slides)

    def on_answer(value: int, result_area, q: Question, idx: int, total: int):
        correct = value == q.answer
        if correct:
            quiz_state['score'] += 1
        quiz_state['results'].append({'q': q, 'selected': value, 'correct': correct})

        with result_area:
            if correct:
                with ui.row().classes('result-row result-correct'):
                    ui.icon('check_circle').classes('result-icon-correct')
                    ui.label(q.options[value]).classes('result-text-correct')
            else:
                with ui.column().classes('gap-2 w-full'):
                    with ui.row().classes('result-row result-wrong'):
                        ui.icon('cancel').classes('result-icon-wrong')
                        ui.label(q.options[value]).classes('result-text-wrong')
                    with ui.row().classes('result-row result-correct'):
                        ui.icon('check_circle').classes('result-icon-correct')
                        ui.label(q.options[q.answer]).classes('result-text-correct')

            next_label = 'Finish' if idx + 1 >= total else 'Next'
            def advance(_=None):
                quiz_state['idx'] += 1
                load_question()
            ui.button(next_label, on_click=advance).props('unelevated color=indigo').classes('w-full mt-2')

    load_question()
    dlg.open()


# ── Quiz page ─────────────────────────────────────────────────────────────────

def quiz_page():
    learner_model = LearnerModel()
    decks = get_decks()
    selected: dict[str, str] = {}

    with ui.element('div').classes('topics-page'):
        with ui.element('div').classes('topics-header'):
            ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round dense')
            ui.label('Quiz').classes('header-title')

        with ui.element('div').classes('topics-body'):
            @ui.refreshable
            def topic_list_view():
                with ui.column().classes('topics-content'):
                    if not decks:
                        ui.label('No decks uploaded yet.').classes('text-sm text-slate-400 italic')
                    for deck in decks:
                        topics = learner_model.get_deck(deck).get('topics', {})
                        if not topics:
                            continue

                        expanded = {'v': True}
                        with ui.element('div').classes('w-full'):
                            with ui.row().classes('topics-deck-row items-center gap-1 w-full') as deck_row:
                                chevron = ui.icon('expand_more').classes('topics-chevron')
                                ui.label(deck).classes('topics-deck-heading')
                            topic_list = ui.column().classes('gap-0 w-full')

                            def make_collapse(icon_el, list_el, state):
                                def toggle(_=None):
                                    state['v'] = not state['v']
                                    list_el.set_visibility(state['v'])
                                    icon_el.set_name('expand_more' if state['v'] else 'chevron_right')
                                return toggle
                            deck_row.on('click', make_collapse(chevron, topic_list, expanded))

                            with topic_list:
                                for topic_name, t in topics.items():
                                    note = t.get('progress')
                                    with ui.element('div').classes('topic-card w-full') as card:
                                        ui.label(topic_name).classes('topic-card-name')
                                        if note:
                                            ui.label(note).classes('topic-card-note')

                                    def make_toggle(name: str, d: str, card_el):
                                        def toggle(_=None):
                                            if name in selected:
                                                del selected[name]
                                                card_el.classes(remove='topic-card-selected')
                                            else:
                                                selected[name] = d
                                                card_el.classes(add='topic-card-selected')
                                            quiz_footer.set_visibility(bool(selected))
                                            n = len(selected)
                                            quiz_btn_ref['btn'].text = f'Start quiz · {n} topic{"s" if n != 1 else ""}'
                                        return toggle
                                    card.on('click', make_toggle(topic_name, deck, card))

            topic_list_view()

        quiz_footer = ui.element('div').classes('topics-footer')
        quiz_footer.set_visibility(False)
        with quiz_footer:
            with ui.element('div').classes('topics-footer-inner'):
                quiz_btn_ref: dict = {}

                async def go_quiz(_=None):
                    topics_to_quiz = list(selected.keys())
                    btn = quiz_btn_ref['btn']
                    btn.props(add='loading disable')
                    await asyncio.sleep(0)
                    try:
                        quiz = await asyncio.to_thread(generate_quiz, topics_to_quiz, DEFAULT_NUM_QUESTIONS, learner_model)
                    except Exception as e:
                        btn.props(remove='loading disable')
                        ui.notify(f'Failed: {e}', type='negative')
                        return
                    btn.props(remove='loading disable')
                    if not quiz.questions:
                        ui.notify('No questions could be generated for those topics.', type='warning')
                        return
                    def on_quiz_close():
                        selected.clear()
                        quiz_footer.set_visibility(False)
                        learner_model._data = learner_model._load()
                        topic_list_view.refresh()
                    open_quiz_overlay(quiz, learner_model, on_close=on_quiz_close)

                quiz_btn_ref['btn'] = ui.button('Start quiz', on_click=go_quiz).props('unelevated color=indigo').classes('w-full')
