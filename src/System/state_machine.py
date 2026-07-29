# ===================================================================================
# NORMAL ──(eye_closed N프레임)──> WARNING ──(eye_closed M프레임)──> ALERT ↑
# └──────────(eye_open)──────────────┘◄───────────────(eye_open)─────────┘
# ===================================================================================

from enum import Enum
from System.define import DetectionResult

class AlertState(Enum):
    NORMAL  = 0
    WARNING = 1
    ALERT   = 2

class DrowsinessStateMachine:
    THRESHOLDS = {AlertState.WARNING: 15, AlertState.ALERT: 45}  # frames

    def __init__(self, event_bus):
        self._state = AlertState.NORMAL
        self._count = 0                     # count frames
        self._bus   = event_bus             # for publishing events

    def update(self, results: list[DetectionResult]):
        pass
