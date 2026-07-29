from time import monotonic, sleep
class Application:
    def __init__(self, target_fps: float = 30.0):
        self._running = False
        self._frame_interval = 1.0 / target_fps if target_fps > 0 else 0.0

    def initialize(self) -> None:
        """프로그램 시작 시 한 번 실행."""
        pass

    def process_input(self) -> None:
        """매 프레임 입력 처리."""
        pass

    def update(self) -> None:
        """매 프레임 로직 처리."""
        pass

    def render(self) -> None:
        """매 프레임 화면 출력."""
        pass

    def shutdown(self) -> None:
        """프로그램 종료 시 한 번 실행."""
        pass

    def run(self) -> None:
        self.initialize()
        self._running = True

        try:
            while self._running:
                frame_started_at = monotonic()

                self.process_input()
                self.update()
                self.render()

                elapsed = monotonic() - frame_started_at
                remaining = self._frame_interval - elapsed

                if remaining > 0:
                    sleep(remaining)
        finally:
            self.shutdown()

    def stop(self) -> None:
        self._running = False