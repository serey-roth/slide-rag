from nicegui import ui


def slide_strip(container, slides: list):
    with container:
        with ui.row().classes('slide-strip'):
            for slide in slides:
                url = '/' + slide['image_path']
                label = f"{slide['deck']} · Slide {slide['slide_num']}"

                def make_open(path, lbl):
                    def open_fullscreen(_=None):
                        with ui.dialog().props('maximized') as dlg:
                            with ui.column().classes('items-center justify-center w-full h-full bg-black'):
                                ui.button(icon='close', on_click=dlg.close).props('flat round color=white').classes('self-end m-2')
                                ui.image(path).classes('max-h-screen max-w-screen object-contain')
                                ui.label(lbl).classes('text-white text-sm mt-2')
                        dlg.open()
                    return open_fullscreen

                with ui.element('div').classes('slide-thumb').on('click', make_open(url, label)):
                    ui.image(url).classes('slide-thumb-img')
                    ui.label(label).classes('slide-thumb-label')


def slides_toggle(slides: list):
    visible = False
    row = ui.row().classes('items-center gap-1')
    container = ui.element('div')
    container.set_visibility(False)

    def toggle(_=None):
        nonlocal visible
        visible = not visible
        container.set_visibility(visible)
        row.clear()
        with row:
            ui.icon('expand_more' if visible else 'chevron_right').classes('text-slate-400 text-sm')
            ui.label('Hide source slides' if visible else 'View source slides').classes('text-xs text-slate-400 cursor-pointer')

    with row:
        ui.icon('chevron_right').classes('text-slate-400 text-sm')
        ui.label('View source slides').classes('text-xs text-slate-400 cursor-pointer')
    row.on('click', toggle)
    slide_strip(container, slides)

