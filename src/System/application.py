import System
from time import monotonic, sleep
class Application:
    def __init__(self, target_fps: float = 30.0):
        self._running = False
        self._frame_interval = 1.0 / target_fps if target_fps > 0 else 0.0

    def __initialize(self) -> None:
        """프로그램 시작 시 한 번 실행."""
        pass

    def __input(self) -> None:
        """매 프레임 입력 처리."""
        pass

    def __update(self) -> None:
        """매 프레임 로직 처리."""
        pass

    def __render(self) -> None:
        """매 프레임 화면 출력."""
        pass

    def shutdown(self) -> None:
        """프로그램 종료 시 한 번 실행."""
        pass

    def run(self) -> None:
        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)

        self._running = True
        self.__initialize()

        try:
            while self._running:
                frame_started_at = monotonic()

                self.__input()
                self.__update()
                self.__render()

                elapsed = monotonic() - frame_started_at
                remaining = self._frame_interval - elapsed

                if remaining > 0:
                    sleep(remaining)
        finally:
            self.shutdown()

    def stop(self) -> None:
        self._running = False