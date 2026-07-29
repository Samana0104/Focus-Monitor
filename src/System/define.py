from dataclasses import dataclass
from enum import Enum, auto

DEBUG = True
# Set to True to enable debug mode, False to disable it.

class LogLevel(Enum):
    NONE = "None"
    WARNING = "Warning"
    DANGER = "Danger"

class TerminalColor(Enum):
    BLACK = "\033[30m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

class EventType(Enum):
    DROWSY_DETECTED = auto()
    PHONE_DETECTED = auto()
    GAZE_AWAY = auto()
    ALERT_CLEARED = auto()


@dataclass
class DetectionResult:
    label: str
    confidence: float
    triggered: bool
    metadata: dict
