from time import monotonic

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Signal,
    QTimer,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
)

from Singleton.Camera import camera_manager
from Singleton.Events import Payload, event_manager
from Singleton.Settings import settings_instance
from Singleton.Timer import timer_manager
from Singleton.EffectSound import effect_sound
from System.Define import EventKey
from System.FunctionLibrary import FunctionLibrary
from UI.UISettingsDialog import UISettingsDialog
from UI.UIMainWindow import UIMainWindow


class NotificationCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("notificationCard")

        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(settings_instance.ui_layout["notification_margin_horizontal"], settings_instance.ui_layout["notification_margin_vertical"], settings_instance.ui_layout["notification_margin_horizontal"], settings_instance.ui_layout["notification_margin_vertical"])
        layout.setSpacing(12)

        self._icon_label: QLabel = QLabel(self)
        self._icon_label.setObjectName("notificationIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(42, 42)
        layout.addWidget(self._icon_label)

        content_layout: QVBoxLayout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(settings_instance.ui_layout["notification_content_spacing"])

        header_layout: QHBoxLayout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._title_label: QLabel = QLabel()
        self._title_label.setObjectName("notificationTitle")
        header_layout.addWidget(self._title_label, 1)

        self._time_label: QLabel = QLabel("0초 전")
        self._time_label.setObjectName("notificationTime")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self._time_label)
        content_layout.addLayout(header_layout)

        self._detail_label: QLabel = QLabel()
        self._detail_label.setObjectName("notificationDetail")
        content_layout.addWidget(self._detail_label)
        layout.addLayout(content_layout, 1)

        self._created_at: float = monotonic()

    def set_content(self, title: str, detail: str = "", icon_name: str = "sleeping.png") -> None:
        self._title_label.setText(title)
        self._detail_label.setText(detail)
        self._detail_label.setVisible(bool(detail))
        self._created_at = monotonic()
        self._time_label.setText("0초 전")

        pixmap = QPixmap(str(FunctionLibrary.get_ui_path() / icon_name))
        self._icon_label.setVisible(not pixmap.isNull())
        if not pixmap.isNull():
            self._icon_label.setPixmap(pixmap.scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_elapsed_time(self, now: float) -> None:
        elapsed_seconds = int(now - self._created_at)
        if elapsed_seconds < 60:
            text = f"{elapsed_seconds}초 전"
        elif elapsed_seconds < 3600:
            text = f"{elapsed_seconds // 60}분 전"
        elif elapsed_seconds < 86400:
            text = f"{elapsed_seconds // 3600}시간 전"
        else:
            text = f"{elapsed_seconds // 86400}일 전"
        self._time_label.setText(text)


class UIHandler(QMainWindow):
    notification_received = Signal(str, str, str)

    def __init__(self) -> None:
        super().__init__()

        self.ui: UIMainWindow = UIMainWindow()
        self.ui.setup_ui(self)
        self._animations: list[QParallelAnimationGroup] = []
        self._is_started: bool = False
        self._ui_settings_dialog: UISettingsDialog = UISettingsDialog(self)
        self._notification_time_timer: QTimer = QTimer(self)
        self._notification_time_timer.setInterval(5000)
        self._notification_time_timer.timeout.connect(self.__update_notification_times)
        self._notification_time_timer.start()
        self.notification_received.connect(self.add_notification)

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
        self.__set_started(False)
        self.__load_icons()
        self.__load_stylesheet()

    def start_requested(self, checked: bool = False) -> None:
        if self._is_started:
            return

        event_manager.publish(EventKey.START_REQUESTED.value)
        self.__show_camera_waiting()
        self.__set_started(self.__start_camera())

    def break_requested(self, checked: bool = False) -> None:
        if not self._is_started:
            return

        event_manager.publish(EventKey.BREAK_REQUESTED.value)
        camera_manager.stop()
        self.__show_camera_waiting()
        self.__set_started(False)

    def open_settings(self, checked: bool = False) -> None:
        self._ui_settings_dialog.show()
        dialog_geometry = self._ui_settings_dialog.frameGeometry()
        dialog_geometry.moveCenter(self.frameGeometry().center())
        self._ui_settings_dialog.move(dialog_geometry.topLeft())
        self._ui_settings_dialog.raise_()
        self._ui_settings_dialog.activateWindow()

    def initialize(self) -> None:
        self.__subscribe_events()
        self.show()
        self.__set_started(self.__start_camera())

    def add_notification(self, title: str, detail: str, icon_name: str) -> None:
        max_count: int = settings_instance.ui_layout["notification_max_count"]
        if max_count <= 0:
            return

        while self.ui.notification_list.count() >= max_count:
            self.__remove_oldest_notification()

        item: QListWidgetItem = QListWidgetItem()
        card: NotificationCard = NotificationCard()
        card.set_content(title, detail, icon_name)
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

        effect_sound.play("notification.wav")

    def set_size(self, width: int, height: int) -> None:
        self.resize(width, height)
        settings_instance["window_width"] = width
        settings_instance["window_height"] = height

    def render(self) -> None:
        if self._is_started != camera_manager.is_running:
            self.__set_started(camera_manager.is_running)

        self.ui.status_label.setText(
            f"FPS: {timer_manager.fps:.1f} | "
            f"Frame: {timer_manager.frame_count}"
        )

    def shutdown(self) -> None:
        self.__unsubscribe_events()
        self._notification_time_timer.stop()
        camera_manager.stop()
        self.__set_started(False)
        self.close()

    def __subscribe_events(self) -> None:
        event_manager.subscribe(EventKey.ABSENCE_DETECTED.value, self.__on_absence_detected)
        event_manager.subscribe(EventKey.DROWSY_DETECTED.value, self.__on_drowsy_detected)
        event_manager.subscribe(EventKey.PHONE_DETECTED.value, self.__on_phone_detected)
        event_manager.subscribe(EventKey.ALERT_CLEARED.value, self.__on_alert_cleared)
        event_manager.subscribe(EventKey.START_REQUESTED.value, self.__on_start_requested)
        event_manager.subscribe(EventKey.BREAK_REQUESTED.value, self.__on_break_requested)

    def __unsubscribe_events(self) -> None:
        event_manager.unsubscribe(EventKey.ABSENCE_DETECTED.value, self.__on_absence_detected)
        event_manager.unsubscribe(EventKey.DROWSY_DETECTED.value, self.__on_drowsy_detected)
        event_manager.unsubscribe(EventKey.PHONE_DETECTED.value, self.__on_phone_detected)
        event_manager.unsubscribe(EventKey.ALERT_CLEARED.value, self.__on_alert_cleared)
        event_manager.unsubscribe(EventKey.START_REQUESTED.value, self.__on_start_requested)
        event_manager.unsubscribe(EventKey.BREAK_REQUESTED.value, self.__on_break_requested)

    def __on_absence_detected(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.ABSENCE_DETECTED, payload)

    def __on_drowsy_detected(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.DROWSY_DETECTED, payload)

    def __on_phone_detected(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.PHONE_DETECTED, payload)

    def __on_alert_cleared(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.ALERT_CLEARED, payload)

    def __on_start_requested(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.START_REQUESTED, payload)

    def __on_break_requested(self, payload: Payload) -> None:
        self.__emit_notification(EventKey.BREAK_REQUESTED, payload)

    def __emit_notification(self, event_key: EventKey, payload: Payload) -> None:
        event_messages = getattr(settings_instance, "event_messages", {})
        if not isinstance(event_messages, dict):
            event_messages = {}

        message = event_messages.get(event_key.value, {})
        if not isinstance(message, dict):
            message = {}

        notification_title = str(payload.get("title", message.get("title", event_key.value)))
        notification_detail = str(payload.get("detail", message.get("detail", "")))
        icon_value = payload.get("icon_name", message.get("icon_name"))
        icon_name = "" if icon_value is None else str(icon_value)
        self.notification_received.emit(notification_title, notification_detail, icon_name)

    def __update_notification_times(self) -> None:
        now: float = monotonic()
        for index in range(self.ui.notification_list.count()):
            item = self.ui.notification_list.item(index)
            card = self.ui.notification_list.itemWidget(item)
            if isinstance(card, NotificationCard):
                card.update_elapsed_time(now)

    def __start_camera(self) -> bool:
        camera_manager.set_video_output(self.ui.camera_video)
        if camera_manager.run():
            self.ui.camera_stack.setCurrentWidget(self.ui.camera_video_page)
            return True

        self.ui.camera_view.setText(camera_manager.last_error)
        self.ui.camera_stack.setCurrentWidget(self.ui.camera_placeholder_page)
        return False

    def __set_started(self, started: bool) -> None:
        self._is_started = bool(started)
        self.ui.start_button.setEnabled(not self._is_started)
        self.ui.break_button.setEnabled(self._is_started)

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
