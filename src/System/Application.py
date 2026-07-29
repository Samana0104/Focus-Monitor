import sys
import System

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from System.FunctionLibrary import FunctionLibrary
from Singleton.Settings import settings_instance
from Singleton.Timer import timer_manager
from UI.UIHandler import UIHandler

class Application:
    def __init__(self):
        self._running : bool = False
        self._qt_app : QApplication = QApplication(sys.argv)
        self._ui : UIHandler = UIHandler()

        self._timer: QTimer = QTimer()
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.__tick)
        self._qt_app.lastWindowClosed.connect(self.stop)


    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def delta_time(self) -> float:
        return timer_manager.delta_time

    @property
    def fps(self) -> float:
        return timer_manager.fps

    @property
    def frame_count(self) -> int:
        return timer_manager.frame_count

    def initialize(self) -> None:
        """Initialize and show application resources once."""

        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)
        settings_instance.load()
        timer_manager.start()
        self._ui.initialize()

    def __update(self) -> None:
        if self._ui.consume_notification_request():
            self._ui.add_notification(
                "알림",
                "숫자 1 키 입력이 감지되었습니다.",
            )

    def __render(self) -> None:
        self._ui.render()
        """Send the latest state to the UI once per frame."""

    def shutdown(self) -> None:
        """Release UI resources once."""
        self._timer.stop()
        timer_manager.stop()
        self._ui.shutdown()

    def __tick(self) -> None:
        if not self._running:
            return

        timer_manager.tick()

        try:
            self.__update()
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
        target_fps: int = max(1, int(settings_instance["target_fps"]))
        interval_ms: int = max(1, round(1000 / target_fps))
        self._timer.start(interval_ms)

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
