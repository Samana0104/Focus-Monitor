from dataclasses import dataclass
from enum import Enum, auto


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
