from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
)

from Singleton.Camera import camera_manager
from Singleton.Settings import settings_instance
from Singleton.Timer import timer_manager
from System.FunctionLibrary import FunctionLibrary
from UI.UISettingsDialog import UISettingsDialog
from UI.UIMainWindow import UIMainWindow


class NotificationCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("notificationCard")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(
            settings_instance.ui_layout["notification_margin_horizontal"],
            settings_instance.ui_layout["notification_margin_vertical"],
            settings_instance.ui_layout["notification_margin_horizontal"],
            settings_instance.ui_layout["notification_margin_vertical"],
        )
        layout.setSpacing(
            settings_instance.ui_layout["notification_content_spacing"]
        )

        self._title_label: QLabel = QLabel()
        self._title_label.setObjectName("notificationTitle")
        layout.addWidget(self._title_label)

        self._detail_label: QLabel = QLabel()
        self._detail_label.setObjectName("notificationDetail")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

    def set_content(self, title: str, detail: str = "") -> None:
        self._title_label.setText(title)
        self._detail_label.setText(detail)
        self._detail_label.setVisible(bool(detail))


class UIHandler(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.ui: UIMainWindow = UIMainWindow()
        self.ui.setup_ui(self)
        self._animations: list[QParallelAnimationGroup] = []
        self._is_on_break: bool = False
        self._ui_settings_dialog: UISettingsDialog = UISettingsDialog(self)

        self.setWindowTitle(settings_instance["window_title"])
        self.resize(
            settings_instance["window_width"],
            settings_instance["window_height"],
        )
        self.ui.camera_video.setAspectRatioMode(
            Qt.AspectRatioMode.KeepAspectRatioByExpanding
        )
        self.ui.start_button.clicked.connect(self.start_requested)
        self.ui.break_button.clicked.connect(self.break_requested)
        self.ui.settings_button.clicked.connect(self.open_settings)
        self.ui.notification_list.verticalScrollBar().rangeChanged.connect(
            self.__keep_notification_scroll_at_bottom
        )
        self.__load_icons()
        self.__load_stylesheet()

    def start_requested(self, checked: bool = False) -> None:
        self._is_on_break = False
        self.__show_camera_waiting()
        self.__start_camera()

    def break_requested(self, checked: bool = False) -> None:
        self._is_on_break = True
        camera_manager.stop()
        self.__show_camera_waiting()

    def open_settings(self, checked: bool = False) -> None:
        self._ui_settings_dialog.show()
        dialog_geometry = self._ui_settings_dialog.frameGeometry()
        dialog_geometry.moveCenter(self.frameGeometry().center())
        self._ui_settings_dialog.move(dialog_geometry.topLeft())
        self._ui_settings_dialog.raise_()
        self._ui_settings_dialog.activateWindow()

    def initialize(self) -> None:
        self.show()
        self.__start_camera()

    def add_notification(self, title: str, detail: str = "") -> None:
        max_count: int = settings_instance.ui_layout["notification_max_count"]
        if max_count <= 0:
            return

        while self.ui.notification_list.count() >= max_count:
            self.__remove_oldest_notification()

        item: QListWidgetItem = QListWidgetItem()
        card: NotificationCard = NotificationCard()
        card.set_content(title, detail)
        target_height: int = settings_instance.ui_layout["notification_height"]
        item.setSizeHint(QSize(0, 0))
        self.ui.notification_list.addItem(item)
        self.ui.notification_list.setItemWidget(item, card)

        opacity_effect: QGraphicsOpacityEffect = QGraphicsOpacityEffect(card)
        opacity_effect.setOpacity(0.0)
        card.setGraphicsEffect(opacity_effect)
        duration: int = settings_instance.ui_layout["notification_animation_ms"]

        opacity_animation: QPropertyAnimation = QPropertyAnimation(
            opacity_effect,
            b"opacity",
        )
        opacity_animation.setDuration(duration)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        height_animation: QVariantAnimation = QVariantAnimation(self)
        height_animation.setDuration(duration)
        height_animation.setStartValue(0)
        height_animation.setEndValue(target_height)
        height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        height_animation.valueChanged.connect(
            lambda value: self.__resize_notification_item(item, int(value))
        )

        group: QParallelAnimationGroup = QParallelAnimationGroup(self)
        group.addAnimation(opacity_animation)
        group.addAnimation(height_animation)
        group.finished.connect(
            lambda: self.__finish_animation(group, item, target_height)
        )
        self._animations.append(group)

        self.ui.notification_list.scrollToBottom()
        group.start()

    def set_size(self, width: int, height: int) -> None:
        self.resize(width, height)
        settings_instance["window_width"] = width
        settings_instance["window_height"] = height

    def render(self) -> None:
        self.ui.status_label.setText(
            f"FPS: {timer_manager.fps:.1f} | "
            f"Frame: {timer_manager.frame_count}"
        )

    def shutdown(self) -> None:
        camera_manager.stop()
        self.close()

    def __start_camera(self) -> None:
        camera_manager.set_video_output(self.ui.camera_video)
        if camera_manager.run():
            self.ui.camera_stack.setCurrentWidget(self.ui.camera_video_page)
            return

        self.ui.camera_view.setText(camera_manager.last_error)
        self.ui.camera_stack.setCurrentWidget(self.ui.camera_placeholder_page)

    def __show_camera_waiting(self) -> None:
        waiting_text: str = str(self.ui.camera_view.property("waitingText"))
        self.ui.camera_view.setText(waiting_text)
        self.ui.camera_stack.setCurrentWidget(self.ui.camera_placeholder_page)

    def __load_stylesheet(self) -> None:
        stylesheet_path = FunctionLibrary.get_ui_path() / "Style.qss"
        if stylesheet_path.exists():
            self.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))

    def __load_icons(self) -> None:
        self.ui.report_button.setIcon(QIcon(str(FunctionLibrary.get_ui_path() / "report_icon.png")))
        self.ui.settings_button.setIcon(QIcon(str(FunctionLibrary.get_ui_path() / "setting_icon.png")))

    def __remove_oldest_notification(self) -> None:
        oldest_item: QListWidgetItem | None = self.ui.notification_list.item(0)
        if oldest_item is None:
            return

        oldest_widget = self.ui.notification_list.itemWidget(oldest_item)
        self.ui.notification_list.removeItemWidget(oldest_item)
        removed_item: QListWidgetItem | None = self.ui.notification_list.takeItem(0)
        if oldest_widget is not None:
            oldest_widget.deleteLater()
        del removed_item

    def __finish_animation(self, animation: QParallelAnimationGroup, item: QListWidgetItem, target_height: int) -> None:
        item.setSizeHint(QSize(0, target_height))
        self.ui.notification_list.scrollToBottom()
        if animation in self._animations:
            self._animations.remove(animation)
        animation.deleteLater()

    def __resize_notification_item(self, item: QListWidgetItem, height: int) -> None:
        item.setSizeHint(QSize(0, height))
        self.ui.notification_list.scrollToBottom()

    def __keep_notification_scroll_at_bottom(self, minimum: int, maximum: int) -> None:
        self.ui.notification_list.verticalScrollBar().setValue(maximum)
