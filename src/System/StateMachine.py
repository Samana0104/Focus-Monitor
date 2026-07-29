# ===================================================================================
# NORMAL ──(eye_closed N프레임)──> WARNING ──(eye_closed M프레임)──> ALERT ↑
# └──────────(eye_open)──────────────┘◄───────────────(eye_open)─────────┘
# ===================================================================================

from enum import Enum
from System.Define import DetectionResult
from System.FunctionLibrary import FunctionLibrary, LogLevel
class AlertState(Enum):
    NORMAL  = 0
    WARNING = 1
    ALERT   = 2

class DrowsinessStateMachine:
    THRESHOLDS = {AlertState.WARNING: 15, AlertState.ALERT: 45}  # frames

    def __init__(self):
        self._state = AlertState.NORMAL
        self._count = 0                     # count consequtive frames
        # self._bus   = event_bus             # for publishing events

    def update(self, results: list[DetectionResult]):
        """
        DetectionResult를 받아 state를 업데이트한다.
        """
        eye = results[0]
        # TODO : Add other detections
        # gaze = 
        # phone = 

        # TODO : Add bus publishing
        THRESHOLDS = {AlertState.WARNING: 15, AlertState.ALERT: 45}  # frames
        if eye.triggered:
            self._count += 1
        else:
            if self._state != AlertState.NORMAL:
                FunctionLibrary.log("ALERT_CLEARED", LogLevel.WARNING)
            self._state = AlertState.NORMAL
            self._count = 0
            return

        for state, thresh in reversed(self.THRESHOLDS.items()):
            if self._count >= thresh and self._state != state:
                self._state = state
                FunctionLibrary.log(state.name, LogLevel.WARNING)
                break
