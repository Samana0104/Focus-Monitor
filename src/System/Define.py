from dataclasses import dataclass
from enum import Enum, auto


DEBUG = True
SETTING_PATH = "config/Settings.json"
UI_STYLE_PATH = "res/ui/Style.qss"

EAR_THRESHOLD = 0.2

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
    DROWSY_DETECTED : str = "DROWSY_DETECTED"
    PHONE_DETECTED : str = "PHONE_DETECTED"
    GAZE_AWAY : str = "GAZE_AWAY"
    ALERT_CLEARED : str = "ALERT_CLEARED"


@dataclass
class DetectionResult:
    label: str
    confidence: float
    triggered: bool
    metadata: dict
