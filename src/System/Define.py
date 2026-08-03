from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


DEBUG = True
SETTING_PATH = "config/Settings.json"
RESOURCE_PATH = "res"


class LogLevel(Enum):
    NONE = "None"
    WARNING = "Warning"
    DANGER = "Danger"


class TerminalColor(Enum):
    BLACK = "\033[30m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"


class EventKey(Enum):
    ABSENCE_DETECTED : str = "ABSENCE_DETECTED"
    DROWSY_DETECTED : str = "DROWSY_DETECTED"
    PHONE_DETECTED : str = "PHONE_DETECTED"
    ALERT_CLEARED : str = "ALERT_CLEARED"
    START_REQUESTED : str = "START_REQUESTED"
    BREAK_REQUESTED : str = "BREAK_REQUESTED"


class FocusState(Enum):
    FOCUSED = "focused"
    PHONE = "phone"
    DROWSY = "drowsy"
    ABSENT = "absent"


class AlertLevel(Enum):
    NONE = 0
    WARNING = 1
    ALERT = 2


class DetectionResult:
    """Result returned by one detector for one camera frame."""

    def __init__(self, label: str, triggered: bool, metadata: dict[str, Any]) -> None:
        self.label = label
        self.triggered = triggered
        self.metadata = metadata


@dataclass(slots=True)
class DebugBox:
    bbox: list[float]
    color: tuple[int, int, int]
    label: str


@dataclass(slots=True)
class DebugText:
    text: str
    origin: tuple[int, int]
    color: tuple[int, int, int]
