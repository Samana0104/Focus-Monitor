from time import monotonic

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Signal,
    QTimer,
    Qt,
    QUrl,
)
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
)

from Singleton.Camera import camera_manager
from Singleton.Events import Payload, event_manager
from Singleton.Settings import settings_instance
from Singleton.Report import report_manager
from Singleton.Timer import timer_manager
from Singleton.EffectSound import effect_sound
from System.Define import EventKey
from System.FunctionLibrary import FunctionLibrary
from UI.UIPopupDialog import UIPopupDialog
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
        self._reset_animation: QPropertyAnimation | None = None
        self._is_started: bool = False
        self._session_started_at: float | None = None
        self._session_elapsed_seconds: float = 0.0
        self._session_timer_callback_id: int | None = None
        self._ui_settings_dialog: UISettingsDialog = UISettingsDialog(self)
        self._notification_time_timer: QTimer = QTimer(self)
        self._notification_time_timer.setInterval(5000)
        self._notification_time_timer.timeout.connect(self.__update_notification_times)
        self._notification_time_timer.start()
        self.notification_received.connect(self.add_notification)

        self.setWindowTitle(settings_instance["window_title"])
        self.setWindowIcon(QIcon(str(FunctionLibrary.get_ui_path() / "app_icon.png")))
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
        self.ui.report_reset_button.clicked.connect(self.reset_report)
        self.ui.report_button.clicked.connect(self.open_report)
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

    def open_report(self, checked: bool = False) -> None:
        try:
            report_path = report_manager.export_html()
        except OSError as error:
            self.show_popup("리포트 생성 실패", str(error), icon=QMessageBox.Icon.Critical)
            return

        self.show_popup("리포트 저장 완료", f"다음 위치에 저장했습니다.\n\n{report_path}", icon=QMessageBox.Icon.Information)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(report_path))):
            self.show_popup("리포트 열기 실패", f"생성된 파일: {report_path}", icon=QMessageBox.Icon.Warning)

    def reset_report(self, checked: bool = False) -> None:
        report_manager.clear()
        self._session_elapsed_seconds = 0.0
        self._session_started_at = monotonic() if self._is_started else None
        self.__update_session_timer()
        self.__animate_notification_reset()

    def show_popup(
        self,
        title: str,
        reason: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
    ) -> QMessageBox.StandardButton:
        popup = UIPopupDialog(title, reason, buttons, icon, self)
        return popup.exec_standard_button()

    def initialize(self) -> None:
        self._session_timer_callback_id = timer_manager.register_callback(self.__update_session_timer, 1000, True)

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
        item.setSizeHint(QSize(0, target_height))
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

        group: QParallelAnimationGroup = QParallelAnimationGroup(self)
        group.addAnimation(opacity_animation)
        group.finished.connect(lambda: self.__finish_animation(group))
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

        self.ui.status_label.setText(f"FPS: {timer_manager.fps:.1f}")

    def shutdown(self) -> None:
        self.__unsubscribe_events()
        if self._session_timer_callback_id is not None:
            timer_manager.unregister_callback(self._session_timer_callback_id)
            self._session_timer_callback_id = None
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
        started = bool(started)
        if started != self._is_started:
            now = monotonic()
            if started:
                self._session_started_at = now
            elif self._session_started_at is not None:
                self._session_elapsed_seconds += now - self._session_started_at
                self._session_started_at = None

        self._is_started = started
        self.ui.start_button.setEnabled(not self._is_started)
        self.ui.break_button.setEnabled(self._is_started)
        self.__update_session_timer()

    def __update_session_timer(self) -> None:
        elapsed_seconds = self._session_elapsed_seconds
        if self._session_started_at is not None:
            elapsed_seconds += monotonic() - self._session_started_at

        total_seconds = max(0, int(elapsed_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.ui.session_timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def __show_camera_waiting(self) -> None:
        waiting_text: str = str(self.ui.camera_view.property("waitingText"))
        self.ui.camera_view.setText(waiting_text)
        self.ui.camera_stack.setCurrentWidget(self.ui.camera_placeholder_page)

    def __load_stylesheet(self) -> None:
        stylesheet_path = FunctionLibrary.get_ui_path() / "Style.qss"
        if stylesheet_path.exists():
            self.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))

    def __load_icons(self) -> None:
        self.ui.report_reset_button.setIcon(QIcon(str(FunctionLibrary.get_ui_path() / "reset_icon.png")))
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

    def __animate_notification_reset(self) -> None:
        if self._reset_animation is not None:
            self._reset_animation.stop()
            self._reset_animation.deleteLater()
            self._reset_animation = None

        for animation in self._animations:
            animation.stop()
            animation.deleteLater()
        self._animations.clear()

        self.__animate_next_notification_removal()

    def __animate_next_notification_removal(self) -> None:
        last_index = self.ui.notification_list.count() - 1
        if last_index < 0:
            self._reset_animation = None
            return

        item = self.ui.notification_list.item(last_index)
        card = self.ui.notification_list.itemWidget(item)
        if card is None:
            self.ui.notification_list.takeItem(last_index)
            self.__animate_next_notification_removal()
            return

        opacity_effect = QGraphicsOpacityEffect(card)
        opacity_effect.setOpacity(1.0)
        card.setGraphicsEffect(opacity_effect)

        self._reset_animation = QPropertyAnimation(opacity_effect, b"opacity", self)
        self._reset_animation.setDuration(55)
        self._reset_animation.setStartValue(1.0)
        self._reset_animation.setEndValue(0.0)
        self._reset_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._reset_animation.finished.connect(lambda: self.__finish_notification_removal(item, card))
        self._reset_animation.start()

    def __finish_notification_removal(self, item: QListWidgetItem, card: QFrame) -> None:
        row = self.ui.notification_list.row(item)
        if row >= 0:
            self.ui.notification_list.removeItemWidget(item)
            removed_item = self.ui.notification_list.takeItem(row)
            del removed_item
        card.deleteLater()

        if self._reset_animation is not None:
            self._reset_animation.deleteLater()
            self._reset_animation = None
        self.__animate_next_notification_removal()

    def __finish_animation(self, animation: QParallelAnimationGroup) -> None:
        if animation in self._animations:
            self._animations.remove(animation)
        animation.deleteLater()

    def __keep_notification_scroll_at_bottom(self, minimum: int, maximum: int) -> None:
        self.ui.notification_list.verticalScrollBar().setValue(maximum)
