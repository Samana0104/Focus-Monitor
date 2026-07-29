from threading import Lock
from typing import Any

import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import (
    QCamera,
    QMediaCaptureSession,
    QMediaDevices,
    QVideoFrame,
    QVideoSink,
)

from Singleton.Singleton import Singleton
from System.Define import LogLevel
from System.FunctionLibrary import FunctionLibrary
from AI.Detector import EyeDetecter


class CameraManager(Singleton):
    """Own the Qt camera and provide its latest frame to UI and AI code."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._running = False
        self._camera: QCamera | None = None
        self._capture_session: QMediaCaptureSession | None = None
        self._video_output: Any | None = None
        self._video_sink: QVideoSink | None = None
        self._frame_lock = Lock()
        self._bgr_frame: np.ndarray | None = None
        self._last_error = ""

        self._detector: EyeDetecter = EyeDetecter()  # Initialize the detector here

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_video_output(self, output: Any) -> None:
        """Attach a QVideoWidget (or another Qt multimedia video output)."""
        self._video_output = output

        if self._capture_session is not None:
            self._capture_session.setVideoOutput(output)

        sink = output.videoSink() if hasattr(output, "videoSink") else None
        self.__connect_video_sink(sink)

    def run(self) -> bool:
        if self._running:
            return True

        devices = QMediaDevices.videoInputs()
        if not devices:
            self._last_error = "사용 가능한 카메라가 없습니다."
            FunctionLibrary.log(self._last_error, LogLevel.DANGER)
            return False

        self._capture_session = QMediaCaptureSession()
        self._camera = QCamera(devices[0])
        self._camera.errorOccurred.connect(self.__on_camera_error)
        self._capture_session.setCamera(self._camera)

        if self._video_output is not None:
            self._capture_session.setVideoOutput(self._video_output)

            if hasattr(self._video_output, "videoSink"):
                sink = self._video_output.videoSink()
            else:
                sink = None

            self.__connect_video_sink(sink)
        else:
            self.__connect_video_sink(QVideoSink())
            self._capture_session.setVideoSink(self._video_sink)

        self._last_error = ""
        self._camera.start()
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False

        if self._camera is not None:
            self._camera.stop()
            self._camera.deleteLater()

        if self._capture_session is not None:
            self._capture_session.setCamera(None)
            self._capture_session.setVideoOutput(None)
            self._capture_session.deleteLater()

        self.__connect_video_sink(None)
        self._camera = None
        self._capture_session = None

        with self._frame_lock:
            self._bgr_frame = None

    def get_frame(self, copy: bool = True) -> np.ndarray | None:
        """Compatibility alias returning the latest BGR frame."""
        return self.get_yolo_frame(copy=copy)

    def get_yolo_frame(self, copy: bool = True) -> np.ndarray | None:
        """Return a uint8 HxWx3 BGR NumPy frame for YOLO/OpenCV."""
        with self._frame_lock:
            if self._bgr_frame is None:
                return None
            return self._bgr_frame.copy() if copy else self._bgr_frame

    def get_mediapipe_frame(self, copy: bool = True) -> np.ndarray | None:
        """Return a uint8 HxWx3 RGB NumPy frame for MediaPipe."""
        with self._frame_lock:
            if self._bgr_frame is None:
                return None

            rgb_frame = self._bgr_frame[:, :, ::-1]
            if copy:
                return np.ascontiguousarray(rgb_frame)
            return rgb_frame

    def set_frame(self, frame: np.ndarray, copy: bool = True) -> None:
        """Replace the shared BGR frame, for optional post-processing."""
        if frame is None:
            FunctionLibrary.log("Cannot set camera frame to None.", LogLevel.WARNING)
            return

        with self._frame_lock:
            self._bgr_frame = frame.copy() if copy else frame

    def __connect_video_sink(self, sink: QVideoSink | None) -> None:
        if self._video_sink is sink:
            return

        if self._video_sink is not None:
            try:
                self._video_sink.videoFrameChanged.disconnect(self.__on_video_frame_changed)
            except RuntimeError:
                pass

        self._video_sink = sink
        if self._video_sink is not None:
            self._video_sink.videoFrameChanged.connect(self.__on_video_frame_changed)

    def __on_video_frame_changed(self, video_frame: QVideoFrame) -> None:
        if not video_frame.isValid():
            return

        image = video_frame.toImage()
        if image.isNull():
            return

        image = image.convertToFormat(QImage.Format.Format_BGR888)
        width = image.width()
        height = image.height()
        bytes_per_line = image.bytesPerLine()

        buffer = np.frombuffer(
            image.bits(),
            dtype=np.uint8,
            count=image.sizeInBytes(),
        )
        bgr_frame = buffer.reshape(height, bytes_per_line)[:, : width * 3]
        bgr_frame = bgr_frame.reshape(height, width, 3).copy()

        with self._frame_lock:
            self._bgr_frame = bgr_frame

        # AI 테스트를 위해 detector를 호출하여 프레임을 처리합니다.
        self._detector.detect(bgr_frame)  # Call the detector with the new frame
        

    def __on_camera_error(self, error: QCamera.Error, message: str) -> None:
        if error == QCamera.Error.NoError:
            return

        self._last_error = message or "알 수 없는 카메라 오류가 발생했습니다."
        self._running = False
        FunctionLibrary.log(self._last_error, LogLevel.DANGER)


camera_manager = CameraManager.get_instance()
