from collections import defaultdict
from typing import Callable

from System.Define import EventType


class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
        return cls._instance

    def subscribe(self, event: EventType, handler: Callable):
        self._subscribers[event].append(handler)

    def publish(self, event: EventType, payload: dict):
        for handler in self._subscribers[event]:
            handler(payload)
