import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import System
from UI.UIHandler import UIHandler


class Application:
    def __init__(self, target_fps: float = 30.0):
        if target_fps <= 0:
            raise ValueError("target_fps must be greater than zero")

        self._running = False
        self._frame_count = 0
        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self._ui = UIHandler()

        self._timer = QTimer()
        self._timer.setInterval(round(1000 / target_fps))
        self._timer.timeout.connect(self._tick)
        self._qt_app.lastWindowClosed.connect(self.stop)

    @property
    def is_running(self) -> bool:
        return self._running

    def initialize(self) -> None:
        """Initialize and show application resources once."""
        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)
        self._ui.initialize()

    def process_input(self) -> None:
        """Process input once per frame."""
        pass

    def update(self) -> None:
        """Update application logic once per frame."""
        self._frame_count += 1

    def render(self) -> None:
        """Send the latest state to the UI once per frame."""
        self._ui.render(f"Running - frame {self._frame_count}")

    def shutdown(self) -> None:
        """Release UI resources once."""
        self._timer.stop()
        self._ui.shutdown()

    def _tick(self) -> None:
        if not self._running:
            return

        try:
            self.process_input()
            self.update()
            self.render()
        except Exception:
            self.stop()
            raise

    def run(self) -> int:
        """Start the Qt event loop and block until the application stops."""
        if self._running:
            raise RuntimeError("Application is already running")

        self.initialize()
        self._running = True
        self._timer.start()

        try:
            return self._qt_app.exec()
        finally:
            self._running = False
            self.shutdown()

    def stop(self) -> None:
        """Stop frame updates and request application shutdown."""
        if not self._running:
            return

        self._running = False
        self._timer.stop()
        self._qt_app.quit()
