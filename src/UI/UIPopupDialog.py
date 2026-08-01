from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QCloseEvent, QColor, QMouseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class UIPopupDialog(QDialog):
    """Frameless 4:3 popup that returns a QMessageBox standard button."""

    BUTTONS = (
        (QMessageBox.StandardButton.No, "아니요", False),
        (QMessageBox.StandardButton.NoToAll, "모두 아니요", False),
        (QMessageBox.StandardButton.Cancel, "취소", False),
        (QMessageBox.StandardButton.Close, "닫기", False),
        (QMessageBox.StandardButton.Discard, "저장 안 함", False),
        (QMessageBox.StandardButton.Reset, "초기화", False),
        (QMessageBox.StandardButton.RestoreDefaults, "기본값 복원", False),
        (QMessageBox.StandardButton.Help, "도움말", False),
        (QMessageBox.StandardButton.Abort, "중단", False),
        (QMessageBox.StandardButton.Ignore, "무시", False),
        (QMessageBox.StandardButton.Retry, "다시 시도", True),
        (QMessageBox.StandardButton.Apply, "적용", True),
        (QMessageBox.StandardButton.Open, "열기", True),
        (QMessageBox.StandardButton.Save, "저장", True),
        (QMessageBox.StandardButton.SaveAll, "모두 저장", True),
        (QMessageBox.StandardButton.Yes, "예", True),
        (QMessageBox.StandardButton.YesToAll, "모두 예", True),
        (QMessageBox.StandardButton.Ok, "확인", True),
    )

    ICONS = {
        QMessageBox.Icon.NoIcon: ("", "neutral"),
        QMessageBox.Icon.Information: ("i", "information"),
        QMessageBox.Icon.Warning: ("!", "warning"),
        QMessageBox.Icon.Critical: ("!", "critical"),
        QMessageBox.Icon.Question: ("?", "question"),
    }

    def __init__(
        self,
        title: str,
        reason: str,
        buttons: QMessageBox.StandardButton,
        icon: QMessageBox.Icon,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("uiPopupDialog")
        self.setWindowTitle(str(title))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(520, 390)

        self._buttons = buttons
        if self._buttons == QMessageBox.StandardButton.NoButton:
            self._buttons = QMessageBox.StandardButton.Ok
        self._selected_button = QMessageBox.StandardButton.NoButton
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity", self)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame(self)
        card.setObjectName("popupCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 55))
        card.setGraphicsEffect(shadow)
        root_layout.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 22, 36, 32)
        card_layout.setSpacing(0)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)
        close_button = QPushButton("×", card)
        close_button.setObjectName("popupCloseButton")
        close_button.setAccessibleName("팝업 닫기")
        close_button.clicked.connect(self.reject)
        top_layout.addWidget(close_button)
        card_layout.addLayout(top_layout)

        symbol, tone = self.ICONS.get(icon, self.ICONS[QMessageBox.Icon.Information])
        icon_label = QLabel(symbol, card)
        icon_label.setObjectName("popupIconBadge")
        icon_label.setProperty("tone", tone)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setVisible(bool(symbol))
        card_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        card_layout.addSpacing(14)

        title_label = QLabel(str(title), card)
        title_label.setObjectName("popupTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)
        card_layout.addSpacing(10)

        reason_label = QLabel(str(reason), card)
        reason_label.setObjectName("popupReason")
        reason_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        reason_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        reason_label.setWordWrap(True)
        card_layout.addWidget(reason_label)
        card_layout.addStretch(1)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        self.__add_buttons(button_layout, card)
        card_layout.addLayout(button_layout)

    @property
    def selected_button(self) -> QMessageBox.StandardButton:
        return self._selected_button

    def exec_standard_button(self) -> QMessageBox.StandardButton:
        super().exec()
        return self._selected_button

    def reject(self) -> None:
        if self._selected_button == QMessageBox.StandardButton.NoButton:
            self._selected_button = self.__reject_button()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._selected_button == QMessageBox.StandardButton.NoButton:
            self._selected_button = self.__reject_button()
        super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        self.__center_on_parent()
        self.setWindowOpacity(0.0)
        self._fade_animation.stop()
        self._fade_animation.setDuration(170)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.start()
        super().showEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window_handle = self.windowHandle()
            if window_handle is not None:
                window_handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def __add_buttons(self, layout: QHBoxLayout, parent: QWidget) -> None:
        default_button: QPushButton | None = None
        for standard_button, text, is_primary in self.BUTTONS:
            if not self._buttons & standard_button:
                continue

            button = QPushButton(text, parent)
            button.setObjectName("popupPrimaryButton" if is_primary else "popupSecondaryButton")
            button.setAccessibleName(text)
            button.setAutoDefault(is_primary)
            button.clicked.connect(lambda checked=False, selected=standard_button: self.__select_button(selected))
            layout.addWidget(button, 1)
            if is_primary:
                default_button = button

        if layout.count() == 0:
            self._buttons = QMessageBox.StandardButton.Ok
            button = QPushButton("확인", parent)
            button.setObjectName("popupPrimaryButton")
            button.setAccessibleName("확인")
            button.setAutoDefault(True)
            button.clicked.connect(lambda checked=False: self.__select_button(QMessageBox.StandardButton.Ok))
            layout.addWidget(button, 1)
            default_button = button

        if default_button is not None:
            default_button.setDefault(True)
            default_button.setFocus()

    def __select_button(self, button: QMessageBox.StandardButton) -> None:
        self._selected_button = button
        self.accept()

    def __reject_button(self) -> QMessageBox.StandardButton:
        for button in (
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Close,
        ):
            if self._buttons & button:
                return button
        return QMessageBox.StandardButton.NoButton

    def __center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            target_center = parent.frameGeometry().center()
        else:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            target_center = screen.availableGeometry().center()

        geometry = self.frameGeometry()
        geometry.moveCenter(target_center)
        self.move(geometry.topLeft())
