from pkg.utils import helper as helper_fn
import os as operating_system


class Service:
    def run(self) -> None:
        helper_fn()
        operating_system.getcwd()


def entry() -> None:
    service = Service()
    service.run()
