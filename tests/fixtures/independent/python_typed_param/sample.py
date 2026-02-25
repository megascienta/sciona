class UserRepo:
    def find(self):
        pass


class Service:
    def __init__(self, repo: UserRepo):
        self.repo = repo

    def fetch(self):
        self.repo.find()
