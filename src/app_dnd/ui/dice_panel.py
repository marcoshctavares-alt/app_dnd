from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app_dnd.dice import ALLOWED_SIDES, Advantage, roll, roll_d20
from app_dnd.ui.theme import ERROR_COLOR


class DicePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_quick_row())
        layout.addWidget(QLabel("Vantagem/desvantagem vale para o d20:"))
        layout.addLayout(self._build_advantage_row())
        layout.addLayout(self._build_expression_row())
        self._build_history_area(layout)

    def _build_quick_row(self) -> QHBoxLayout:
        quick = QHBoxLayout()
        for sides in (4, 6, 8, 10, 12, 20, 100):
            assert sides in ALLOWED_SIDES
            btn = QPushButton(f"d{sides}")
            btn.clicked.connect(lambda _=False, s=sides: self._quick_roll(s))
            quick.addWidget(btn)
        return quick

    def _build_advantage_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self._adv_group = QButtonGroup(self)
        self._radios: dict[Advantage, QRadioButton] = {}
        for adv, label in (
            (Advantage.NONE, "Normal"),
            (Advantage.ADVANTAGE, "Vantagem"),
            (Advantage.DISADVANTAGE, "Desvantagem"),
        ):
            radio = QRadioButton(label)
            self._adv_group.addButton(radio)
            self._radios[adv] = radio
            row.addWidget(radio)
        self._radios[Advantage.NONE].setChecked(True)
        return row

    def _build_expression_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self._expr = QLineEdit()
        self._expr.setPlaceholderText("Ex.: 2d6+3, 4d6kh3")
        self._expr.returnPressed.connect(self._expression_roll)
        go = QPushButton("Rolar")
        go.clicked.connect(self._expression_roll)
        row.addWidget(self._expr)
        row.addWidget(go)
        return row

    def _build_history_area(self, layout: QVBoxLayout) -> None:
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {ERROR_COLOR};")
        layout.addWidget(self._status)

        self._history = QListWidget()
        layout.addWidget(self._history)
        clear = QPushButton("Limpar histórico")
        clear.clicked.connect(self._history.clear)
        layout.addWidget(clear)

    def selected_advantage(self) -> Advantage:
        for adv, radio in self._radios.items():
            if radio.isChecked():
                return adv
        return Advantage.NONE

    def add_history(self, text: str) -> None:
        self._history.insertItem(0, text)

    def _quick_roll(self, sides: int) -> None:
        self._status.clear()
        if sides == 20:
            result = roll_d20(0, self.selected_advantage())
        else:
            result = roll(f"1d{sides}")
        self.add_history(str(result))

    def _expression_roll(self) -> None:
        text = self._expr.text().strip()
        if not text:
            return
        try:
            self._status.clear()
            self.add_history(str(roll(text)))
        except ValueError as exc:
            self._status.setText(str(exc))
