from time import monotonic, sleep

import System


class Application:
    def __init__(self, target_fps: float = 30.0):
        self._running = False
        self._frame_interval = 1.0 / target_fps if target_fps > 0 else 0.0

    def initialize(self) -> None:
        """Run once when the application starts."""
        System.FunctionLibrary.log("Application is starting...", System.LogLevel.NONE)

    def process_input(self) -> None:
        """Process input once per frame."""
        pass

    def update(self) -> None:
        """Update application logic once per frame."""
        pass

    def render(self) -> None:
        """Render output once per frame."""
        pass

    def shutdown(self) -> None:
        """Run once when the application stops."""
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
