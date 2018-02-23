from abc import ABC


class BaseCC(ABC):

    @classmethod
    def event(self, event_name, info):
        pass


