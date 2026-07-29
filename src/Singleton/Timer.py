from time import monotonic

from Singleton.Singleton import Singleton


class TimerManager(Singleton):
    """Track application frame timing only."""

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

    def start(self) -> None:
        self.reset()
        current_time: float = monotonic()
        self._running = True
        self._started_time = current_time
        self._last_frame_time = current_time
        self._fps_sample_started_time = current_time

    def tick(self) -> None:
        if not self._running:
            return

        current_time: float = monotonic()
        raw_delta: float = current_time - self._last_frame_time
        self._last_frame_time = current_time
        self._delta_time = max(raw_delta, 1e-6)
        self._frame_count += 1
        self._fps_sample_frame_count += 1

        sample_elapsed: float = current_time - self._fps_sample_started_time
        if sample_elapsed >= self._fps_update_interval:
            self._fps = self._fps_sample_frame_count / sample_elapsed
            self._fps_sample_started_time = current_time
            self._fps_sample_frame_count = 0

    def stop(self) -> None:
        self._running = False

    def reset(self) -> None:
        self._running = False
        self._started_time = 0.0
        self._last_frame_time = 0.0
        self._delta_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._fps_sample_started_time = 0.0
        self._fps_sample_frame_count = 0


timer_manager: TimerManager = TimerManager.get_instance()
