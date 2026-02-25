class Service:
    def run(self):
        pass

class Controller:
    def __init__(self):
        self.svc = Service()

    def handle(self):
        self.svc.run()
