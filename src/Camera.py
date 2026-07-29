import cv2
import System

class CameraWorker:
    def __init__(self, pipeline, state_machine):
        super().__init__()
        self._running = False
        self._pipeline = pipeline
        self._sm = state_machine

    def run(self) -> None:
        """Run the detection pipeline and update the state machine."""
        if self._running:
            raise RuntimeError("Application is already running")

        self._running = True
        self._cap = cv2.VideoCapture(0)

        while self._running:
            ret, frame = self._cap.read()

            if not ret:
                raise RuntimeError("Cannot read frame")

            result = self._pipeline.run(frame)
            self._sm.update(result)

    def cleanup(self) -> None:
        self._cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self.cleanup()