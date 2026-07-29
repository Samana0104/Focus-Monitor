from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from Singleton.Settings import settings_instance
from Singleton.Camera import camera_manager
from PySide6.QtWidgets import QFrame
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Singleton.Settings import settings_instance


class NotificationCard(QFrame):
    def __init__(self, title: str, detail: str = ""):
        super().__init__()
        self.setObjectName("notificationCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName("notificationTitle")
        layout.addWidget(title_label)

        if detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("notificationDetail")
            detail_label.setWordWrap(True)
            layout.addWidget(detail_label)


class UIHandler(QMainWindow):

    def __init__(self):
        super().__init__()

        self._layout_settings = getattr(settings_instance, "ui_layout", {})
        self._animations: list[QParallelAnimationGroup] = []
        self._pixmap = QPixmap()
        self._is_on_break = False
        self._camera_panel = self.__create_camera_panel()

        self.setWindowTitle(settings_instance["window_title"])
        self.resize(
            settings_instance["window_width"],
            settings_instance["window_height"],
        )

        central_widget = QWidget()
        central_widget.setObjectName("mainRoot")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        margin = self._layout_settings.get("window_margin", 16)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(self._layout_settings.get("panel_spacing", 16))

        main_layout.addWidget(self._camera_panel, stretch=3)
        main_layout.addWidget(self.__create_side_panel(), stretch=1)

        self.setStyleSheet(getattr(settings_instance, "ui_stylesheet", ""))

    def start_requested(self, checked: bool = False) -> None:
        self._is_on_break = False
        self._camera_label.setText("카메라 연결을 기다리는 중입니다")
        camera_manager.run()

    def break_requested(self, checked: bool = False) -> None:
        self._is_on_break = True
        camera_manager.stop()
        self._pixmap = QPixmap()
        self._camera_label.clear()
        self._camera_label.setText("카메라 연결을 기다리는 중입니다")


    def __create_camera_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("cameraPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._camera_label = QLabel("카메라 연결을 기다리는 중입니다")
        self._camera_label.setObjectName("cameraView")
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setMinimumSize(640, 360)

        self._status_label = QLabel("준비됨")
        self._status_label.setObjectName("statusLabel")

        layout.addWidget(self._camera_label, stretch=1)
        layout.addWidget(self._status_label)
        return panel

    def __create_side_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setMinimumWidth(self._layout_settings.get("side_min_width", 340))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._notification_list = QListWidget()
        self._notification_list.setObjectName("notificationList")
        self._notification_list.setSpacing(8)
        self._notification_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._notification_list.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )

        self._start_button = QPushButton(
            self._layout_settings.get("start_button_text", "시작")
        )
        self._start_button.setObjectName("primaryButton")
        self._start_button.setMinimumHeight(
            self._layout_settings.get("button_height", 52)
        )
        self._start_button.clicked.connect(self.start_requested)

        self._break_button = QPushButton(
            self._layout_settings.get("break_button_text", "쉬는 시간")
        )
        self._break_button.setObjectName("breakButton")
        self._break_button.setMinimumHeight(
            self._layout_settings.get("button_height", 52)
        )
        self._break_button.clicked.connect(self.break_requested)

        layout.addWidget(self._notification_list, stretch=1)
        layout.addWidget(self._start_button)
        layout.addWidget(self._break_button)
        return panel

    def initialize(self) -> None:
        self.show()

    def add_notification(self, title: str, detail: str = "") -> None:
        """Insert an animated rectangular notification at the top."""
        card = NotificationCard(title, detail)
        target_height = self._layout_settings.get("notification_height", 76)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, target_height))
        self._notification_list.insertItem(0, item)
        self._notification_list.setItemWidget(item, card)

        opacity_effect = QGraphicsOpacityEffect(card)
        opacity_effect.setOpacity(0.0)
        card.setGraphicsEffect(opacity_effect)
        card.setMaximumHeight(0)

        duration = self._layout_settings.get("notification_animation_ms", 260)

        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_animation.setDuration(duration)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        height_animation = QPropertyAnimation(card, b"maximumHeight")
        height_animation.setDuration(duration)
        height_animation.setStartValue(0)
        height_animation.setEndValue(target_height)
        height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_animation)
        group.addAnimation(height_animation)
        group.finished.connect(lambda: self.__finish_animation(group, card))
        self._animations.append(group)
        group.start()

        max_count = self._layout_settings.get("notification_max_count", 30)
        while self._notification_list.count() > max_count:
            self._notification_list.takeItem(self._notification_list.count() - 1)

    def __finish_animation(
        self,
        animation: QParallelAnimationGroup,
        card: NotificationCard,
    ) -> None:
        card.setMaximumHeight(16777215)
        if animation in self._animations:
            self._animations.remove(animation)
        animation.deleteLater()

    def __set_camera_pixmap(self, frame) -> None:
        height, width = frame.shape[:2]
        bytes_per_line = frame.strides[0]

        if frame.ndim == 2:
            image_format = QImage.Format.Format_Grayscale8
        elif frame.shape[2] == 3:
            image_format = QImage.Format.Format_BGR888
        elif frame.shape[2] == 4:
            image_format = QImage.Format.Format_ARGB32
        else:
            raise ValueError(f"Unsupported camera frame shape: {frame.shape}")

        image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            image_format,
        )
        self._pixmap = QPixmap.fromImage(image).scaled(
            self._camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._camera_label.setPixmap(self._pixmap)

    def set_size(self, width: int, height: int) -> None:
        self.resize(width, height)
        settings_instance["window_width"] = width
        settings_instance["window_height"] = height

    def render(self, status: str) -> None:
        self._status_label.setText(status)

        if self._is_on_break:
            return

        frame = camera_manager.get_frame(copy=False)
        if frame is not None:
            self.__set_camera_pixmap(frame)

    def shutdown(self) -> None:
        self.close()
