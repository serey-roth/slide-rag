from nicegui import ui

from src.learner_model import LearnerModel
from src.ui.dashboard import build_dashboard


def index():
    learner_model = LearnerModel()
    root = ui.element('div').classes('w-full h-full')
    build_dashboard(root, learner_model)
