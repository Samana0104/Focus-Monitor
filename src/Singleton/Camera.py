from threading import Lock
from typing import Any

import cv2
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
from System.Define import DEBUG, DebugBox, DebugText, LogLevel
from System.FunctionLibrary import FunctionLibrary


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
        self._display_sink: QVideoSink | None = None
        self._frame_lock = Lock()
        self._bgr_frame: np.ndarray | None = None
        self._frame_version: int = 0
        self._last_debug_frame_version: int = -1
        self._last_error = ""

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_video_output(self, output: Any) -> None:
        """Attach a QVideoWidget (or another Qt multimedia video output)."""
        self._video_output = output
        if hasattr(output, "videoSink"):
            self._display_sink = output.videoSink()
        else:
            self._display_sink = None

        if self._capture_session is not None:
            if DEBUG:
                self.__attach_debug_video_sink()
            else:
                self._capture_session.setVideoOutput(output)
                self.__connect_video_sink(self._display_sink)

        elif not DEBUG:
            self.__connect_video_sink(self._display_sink)

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
            if DEBUG:
                self.__attach_debug_video_sink()
            else:
                self._capture_session.setVideoOutput(self._video_output)
                self.__connect_video_sink(self._display_sink)
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
            self._capture_session.setVideoSink(None)
            self._capture_session.deleteLater()

        self.__connect_video_sink(None)
        self._camera = None
        self._capture_session = None
        self._display_sink = None

        with self._frame_lock:
            self._bgr_frame = None
            self._frame_version = 0
            self._last_debug_frame_version = -1

    def get_frame(self, copy: bool = True) -> np.ndarray | None:
        """Compatibility alias returning the latest BGR frame."""
        return self.get_yolo_frame(copy=copy)

    def get_yolo_frame(self, copy: bool = True) -> np.ndarray | None:
        """Return a uint8 HxWx3 BGR NumPy frame for YOLO/OpenCV."""
        with self._frame_lock:
            if self._bgr_frame is None:
                return None
            if copy:
                return self._bgr_frame.copy()
            return self._bgr_frame

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
            if copy:
                self._bgr_frame = frame.copy()
            else:
                self._bgr_frame = frame

    def draw_debug_frame(self, boxes: list[DebugBox], texts: list[DebugText]) -> None:
        if not DEBUG or self._display_sink is None:
            return

        with self._frame_lock:
            if self._bgr_frame is None or self._last_debug_frame_version == self._frame_version:
                return

            frame = self._bgr_frame
            self._last_debug_frame_version = self._frame_version

        self.__show_debug_frame(frame, boxes, texts)

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

    def __attach_debug_video_sink(self) -> None:
        if self._capture_session is None:
            return

        self._capture_session.setVideoOutput(None)
        self.__connect_video_sink(QVideoSink())
        self._capture_session.setVideoSink(self._video_sink)

    def __show_debug_frame(self, frame: np.ndarray, boxes: list[DebugBox], texts: list[DebugText]) -> None:
        height, width = frame.shape[:2]
        image = QImage(frame.data, width, height, frame.strides[0], QImage.Format.Format_BGR888).copy()
        buffer = np.frombuffer(image.bits(), dtype=np.uint8, count=image.sizeInBytes())
        debug_frame = buffer.reshape(height, image.bytesPerLine())[:, : width * 3].reshape(height, width, 3)
        self.__draw_debug_overlay(debug_frame, boxes, texts)
        self._display_sink.setVideoFrame(QVideoFrame(image))

    def __draw_debug_overlay(self, frame: np.ndarray, boxes: list[DebugBox], texts: list[DebugText]) -> None:
        for box in boxes:
            self.__draw_box(frame, box.bbox, box.color, box.label)

        for text in texts:
            self.__draw_text(frame, text.text, text.origin, text.color)

    def __draw_box(self, frame: np.ndarray, bbox: list[float], color: tuple[int, int, int], label: str) -> None:
        frame_height, frame_width = frame.shape[:2]
        x1, y1, x2, y2 = [int(value) for value in bbox]
        x1 = max(0, min(frame_width - 1, x1))
        y1 = max(0, min(frame_height - 1, y1))
        x2 = max(0, min(frame_width - 1, x2))
        y2 = max(0, min(frame_height - 1, y2))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        self.__draw_text(frame, label, (x1, max(20, y1 - 8)), color)

    def __draw_text(self, frame: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
        cv2.putText(
            frame,
            text,
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

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

        buffer = np.frombuffer(image.bits(), dtype=np.uint8, count=image.sizeInBytes())
        bgr_frame = buffer.reshape(height, bytes_per_line)[:, : width * 3]
        bgr_frame = bgr_frame.reshape(height, width, 3).copy()

        with self._frame_lock:
            self._bgr_frame = bgr_frame
            self._frame_version += 1
        

    def __on_camera_error(self, error: QCamera.Error, message: str) -> None:
        if error == QCamera.Error.NoError:
            return

        self._last_error = message or "알 수 없는 카메라 오류가 발생했습니다."
        self._running = False
        FunctionLibrary.log(self._last_error, LogLevel.DANGER)


camera_manager = CameraManager.get_instance()
