from .services import Service as S
from .helpers import run as helper_run


class Controller:
    def __init__(self):
        self.svc = S()

    def handle(self):
        self.svc.run()
        helper_run()
