from time import monotonic
import cv2

class Application:
    def __init__(self, target_fps: float = 30.0):
        if target_fps < 0:
            raise ValueError("target_fps must be zero or greater")

        self._frame_interval = 1.0 / target_fps if target_fps else 0.0
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def run(self) -> None:
        if self._running:
            raise RuntimeError("Application is already running")

        self._capture = cv2.VideoCapture(0)
        self._running = True

        # try:
        #     while not self._stop_event.is_set():
        #         frame_started_at = monotonic()
        #         captured, frame = self._capture.read()

        #         if not captured:
        #             raise RuntimeError("Failed to capture a frame from the camera")

        #         results = self._pipeline.run(frame)
        #         self._state_machine.update(results)

        #         remaining = self._frame_interval - (monotonic() - frame_started_at)
        #         if remaining > 0:
        #             self._stop_event.wait(remaining)
        # finally:
        #     self._running = False
        #     if self._capture is not None:
        #         self._capture.release()
        #         self._capture = None

    def stop(self) -> None:
        pass
