import sys
import System
from time import monotonic

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from System.FunctionLibrary import FunctionLibrary
from Singleton.Settings import settings_instance
from UI.UIHandler import UIHandler

from Singleton.Camera import camera_manager

class Application:
    def __init__(self):
        self._running : bool = False
        self._frame_count : int = 0
        self._delta_time : float = 0.0
        self._current_fps : float = 0.0
        self._last_tick_time : float = 0.0
        self._qt_app : QApplication = QApplication(sys.argv)
        self._ui : UIHandler = UIHandler()

        self._timer = QTimer()
        self._timer.timeout.connect(self.__tick)
        self._qt_app.lastWindowClosed.connect(self.stop)


    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def delta_time(self) -> float:
        return self._delta_time

    @property
    def fps(self) -> float:
        return self._current_fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def initialize(self) -> None:
        """Initialize and show application resources once."""

        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)
        settings_instance.load()
        self._ui.initialize()

    def __update(self, delta_time: float) -> None:
        camera_manager.update()
        self._frame_count += 1

    def __render(self) -> None:
        pass
        self._ui.render(f"FPS: {self._current_fps:.2f}, Frame Count: {self._frame_count}")
        """Send the latest state to the UI once per frame."""

    def shutdown(self) -> None:
        """Release UI resources once."""
        self._timer.stop()
        camera_manager.stop()
        self._ui.shutdown()

    def __tick(self) -> None:
        if not self._running:
            return

        current_time = monotonic()
        raw_delta = current_time - self._last_tick_time
        self._last_tick_time = current_time

        # 0이 되는 경우를 방지하기 위해 최소값을 설정합니다
        self._delta_time = max(raw_delta, 1e-6)

        if self._delta_time > 0:
            self._current_fps = 1.0 / self._delta_time

        FunctionLibrary.log(f"Frame {self._frame_count} processed in {self._current_fps:.1f} seconds.", System.LogLevel.NONE)

        try:
            self.__update(self._delta_time)
            self.__render()
        except Exception:
            self.stop()
            raise


    def run(self) -> int:
        """Start the Qt event loop and block until the application stops."""
        if self._running:
            FunctionLibrary.log("Application is already running.", System.LogLevel.WARNING)
            return

        self.initialize()
        self._running = True
        self._last_tick_time = monotonic()

        self._timer.start()

        try:
            return self._qt_app.exec()
        except Exception as e:
            FunctionLibrary.log(f"An error occurred during application execution: {e}", System.LogLevel.DANGER)
        finally:
            self._running = False
            self.shutdown()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        self._timer.stop()
        self._qt_app.quit()

        settings_instance.save()
