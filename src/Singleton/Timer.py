from dataclasses import dataclass
from time import monotonic
from typing import Callable

from PySide6.QtCore import QTimer, Qt

from Singleton.Settings import settings_instance
from Singleton.Singleton import Singleton


@dataclass(slots=True)
class _ScheduledCallback:
    callback: Callable[[], None]
    interval_ms: int
    repeat: bool
    next_run_time_ms: float


class TimerManager(Singleton):
    """Track application timing and execute scheduled callbacks."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized: bool = True
        self._running: bool = False
        self._started_time: float = 0.0
        self._last_frame_time: float = 0.0
        self._delta_time: float = 0.0
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._fps_update_interval: float = 1.0
        self._fps_sample_started_time: float = 0.0
        self._fps_sample_frame_count: int = 0
        self._callbacks: dict[int, _ScheduledCallback] = {}
        self._next_callback_id: int = 1
        self._timer: QTimer | None = None
        self._target_fps: float = 0.0
        self._target_frame_time: float = 0.0
        self._next_frame_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def delta_time(self) -> float:
        return self._delta_time

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def average_fps(self) -> float:
        elapsed_time: float = self._last_frame_time - self._started_time
        if elapsed_time <= 0.0:
            return 0.0
        return self._frame_count / elapsed_time

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def target_frame_time(self) -> float:
        return self._target_frame_time

    @property
    def target_fps(self) -> float:
        return self._target_fps

    def start(self) -> None:
        if self._running:
            return

        self.reset()
        current_time: float = monotonic()
        self._running = True
        self._target_fps = max(1.0, float(settings_instance["target_fps"]))
        self._target_frame_time = 1.0 / self._target_fps
        self._next_frame_time = current_time + self._target_frame_time
        self._started_time = current_time
        self._last_frame_time = current_time
        self._fps_sample_started_time = current_time

        if self._timer is None:
            self._timer = QTimer()
            self._timer.setSingleShot(False)
            self._timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._timer.timeout.connect(self.__tick)

        self._timer.start(0)

    def register_callback(self, callback: Callable[[], None], interval_ms: int = 0, repeat: bool = True) -> int:
        if interval_ms < 0:
            raise ValueError("interval_ms must be 0 or greater")

        callback_id = self._next_callback_id
        self._next_callback_id += 1
        current_time_ms = monotonic() * 1000.0
        self._callbacks[callback_id] = _ScheduledCallback(callback, interval_ms, repeat, current_time_ms + interval_ms)
        return callback_id

    def unregister_callback(self, callback_id: int) -> bool:
        return self._callbacks.pop(callback_id, None) is not None

    def clear_callbacks(self) -> None:
        self._callbacks.clear()

    def __tick(self) -> None:
        if not self._running:
            return

        current_time: float = monotonic()
        if current_time < self._next_frame_time:
            return

        raw_delta: float = current_time - self._last_frame_time
        self._last_frame_time = current_time
        self._next_frame_time += self._target_frame_time
        if self._next_frame_time <= current_time:
            self._next_frame_time = current_time + self._target_frame_time

        self._delta_time = max(raw_delta, 1e-6)
        self._frame_count += 1
        self._fps_sample_frame_count += 1

        sample_elapsed: float = current_time - self._fps_sample_started_time
        if sample_elapsed >= self._fps_update_interval:
            self._fps = self._fps_sample_frame_count / sample_elapsed
            self._fps_sample_started_time = current_time
            self._fps_sample_frame_count = 0

        self.__tick_callbacks(current_time * 1000.0)

    def __tick_callbacks(self, current_time_ms: float) -> None:
        for callback_id, scheduled_callback in list(self._callbacks.items()):
            if self._callbacks.get(callback_id) is not scheduled_callback:
                continue

            if current_time_ms < scheduled_callback.next_run_time_ms:
                continue

            if scheduled_callback.repeat:
                scheduled_callback.next_run_time_ms = current_time_ms + scheduled_callback.interval_ms
            else:
                self._callbacks.pop(callback_id, None)

            scheduled_callback.callback()

    def stop(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.stop()

    def reset(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.stop()

        self._target_fps = 0.0
        self._target_frame_time = 0.0
        self._next_frame_time = 0.0
        self._started_time = 0.0
        self._last_frame_time = 0.0
        self._delta_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._fps_sample_started_time = 0.0
        self._fps_sample_frame_count = 0


timer_manager: TimerManager = TimerManager.get_instance()
