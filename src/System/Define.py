from enum import Enum, auto


DEBUG = True
SETTING_PATH = "config/Settings.json"
UI_STYLE_PATH = "res/ui/Style.qss"

EAR_THRESHOLD = 0.2
SIMILARITY_THRESHOLD = 0.65


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


class DetectionResult:
    """Result returned by one detector for one camera frame."""

    def __init__(self, label, triggered, metadata):
        self.label = label
        self.triggered = triggered
        self.metadata = metadata
