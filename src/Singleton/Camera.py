from collections.abc import Callable
from threading import Lock
from typing import Any

import cv2
import numpy as np

from Singleton.Singleton import Singleton
from AI.Detector import DetectionPipeline
from System.StateMachine import DrowsinessStateMachine
from System.FunctionLibrary import FunctionLibrary
from System.Define import LogLevel

class CameraManager(Singleton):
    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._running : bool = False
        self._pipeline : DetectionPipeline = DetectionPipeline()
        self._state_machine : DrowsinessStateMachine = DrowsinessStateMachine()
        self._camera_index : int = 0
        self._capture : cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    def run(self) -> None:
        if self._running:
            FunctionLibrary.log("CameraManager is already running.", LogLevel.WARNING)
            return

        self._capture = cv2.VideoCapture(self._camera_index)

        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            FunctionLibrary.log(f"Cannot open camera {self._camera_index}", level=LogLevel.DANGER)
            return

        self._running = True

    def update(self) -> None:
        if not self._running or self._capture is None:
            return

        captured, frame = self._capture.read()
        if not captured:
            self._capture.release()
            self._capture = None
            FunctionLibrary.log(f"Cannot read frame from camera {self._camera_index}", level=LogLevel.DANGER)
            return

        if frame is None:
            FunctionLibrary.log(f"Frame is None from camera {self._camera_index}", level=LogLevel.DANGER)
            return

        self._frame = frame

        # results = self._pipeline.run(frame)
        # self._state_machine.update(results)

    def get_frame(self, copy: bool = True) -> np.ndarray | None:
        """Return the latest captured frame."""
        if self._frame is None:
            return None

        if copy:
            return self._frame.copy()
        else:
            return self._frame

    def set_frame(self, frame: np.ndarray, copy: bool = True) -> None:
        """Replace the shared frame."""
        if frame is None:
            FunctionLibrary.log("Cannot set frame to None.", LogLevel.WARNING)
            return

        if copy:
            self._frame = frame.copy()
        else:
            self._frame = frame

    def modify_frame(self, modifier: Callable[[np.ndarray], None]) -> bool:
        if self._frame is None:
            return False

        modifier(self._frame)
        return True

    def stop(self) -> None:
        self._running = False

        if self._capture is not None:
            self._capture.release()
            self._capture = None

        self._frame = None

        cv2.destroyAllWindows()

camera_manager = CameraManager().get_instance()