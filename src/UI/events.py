from collections import defaultdict
from typing import Callable
from enum import Enum, auto

class EventType(Enum):
    DROWSY_DETECTED    = auto()
    PHONE_DETECTED     = auto()
    GAZE_AWAY          = auto()
    ALERT_CLEARED      = auto()

class EventBus:
    _instance = None  # Singleton

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
