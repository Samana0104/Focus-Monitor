from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class UIHandler(QMainWindow):
    """Own and update the application's main window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OnDevice AI")
        self.resize(960, 640)

        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def initialize(self) -> None:
        """Show the main window."""
        self.show()

    def render(self, status: str) -> None:
        """Render the latest application state."""
        self._status_label.setText(status)

    def shutdown(self) -> None:
        """Close the main window."""
        self.close()
