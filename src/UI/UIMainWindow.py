from PySide6.QtCore import QSize, Qt
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class UIMainWindow:
    """Create and expose the main-window widgets and layouts."""

    def __init__(self) -> None:
        self.main_root: QWidget
        self.main_layout: QHBoxLayout
        self.camera_panel: QFrame
        self.camera_layout: QVBoxLayout
        self.camera_stack: QStackedWidget
        self.camera_placeholder_page: QWidget
        self.camera_view: QLabel
        self.camera_video_page: QWidget
        self.camera_video: QVideoWidget
        self.status_label: QLabel
        self.side_panel: QFrame
        self.side_layout: QVBoxLayout
        self.notification_list: QListWidget
        self.start_button: QPushButton
        self.break_button: QPushButton

    def setup_ui(self, window: QMainWindow) -> None:
        self.main_root = QWidget(window)
        self.main_root.setObjectName("mainRoot")
        self.main_layout = QHBoxLayout(self.main_root)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)

        self.__setup_camera_panel()
        self.__setup_side_panel()

        self.main_layout.addWidget(self.camera_panel, 3)
        self.main_layout.addWidget(self.side_panel, 1)
        window.setCentralWidget(self.main_root)

    def __setup_camera_panel(self) -> None:
        self.camera_panel = QFrame(self.main_root)
        self.camera_panel.setObjectName("cameraPanel")
        self.camera_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.camera_layout = QVBoxLayout(self.camera_panel)
        self.camera_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_layout.setSpacing(10)

        self.camera_stack = QStackedWidget(self.camera_panel)
        self.camera_stack.setObjectName("cameraStack")
        self.camera_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.camera_placeholder_page = QWidget()
        placeholder_layout: QVBoxLayout = QVBoxLayout(
            self.camera_placeholder_page
        )
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_view = QLabel("카메라 연결을 기다리는 중입니다")
        self.camera_view.setObjectName("cameraView")
        self.camera_view.setMinimumSize(QSize(640, 360))
        self.camera_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_view.setProperty(
            "waitingText",
            "카메라 연결을 기다리는 중입니다",
        )
        placeholder_layout.addWidget(self.camera_view)
        self.camera_stack.addWidget(self.camera_placeholder_page)

        self.camera_video_page = QWidget()
        video_layout: QVBoxLayout = QVBoxLayout(self.camera_video_page)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_video = QVideoWidget(self.camera_video_page)
        self.camera_video.setObjectName("cameraVideo")
        self.camera_video.setMinimumSize(QSize(640, 360))
        video_layout.addWidget(self.camera_video)
        self.camera_stack.addWidget(self.camera_video_page)

        self.status_label = QLabel("준비됨", self.camera_panel)
        self.status_label.setObjectName("statusLabel")
        self.camera_layout.addWidget(self.camera_stack, 1)
        self.camera_layout.addWidget(self.status_label)

    def __setup_side_panel(self) -> None:
        self.side_panel = QFrame(self.main_root)
        self.side_panel.setObjectName("sidePanel")
        self.side_panel.setMinimumWidth(340)
        self.side_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.side_layout = QVBoxLayout(self.side_panel)
        self.side_layout.setContentsMargins(0, 0, 0, 0)
        self.side_layout.setSpacing(12)

        self.notification_list = QListWidget(self.side_panel)
        self.notification_list.setObjectName("notificationList")
        self.notification_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.notification_list.setSpacing(8)
        self.notification_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.start_button = QPushButton("시작", self.side_panel)
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(52)
        self.break_button = QPushButton("쉬는 시간", self.side_panel)
        self.break_button.setObjectName("breakButton")
        self.break_button.setMinimumHeight(52)

        self.side_layout.addWidget(self.notification_list, 1)
        self.side_layout.addWidget(self.start_button)
        self.side_layout.addWidget(self.break_button)
