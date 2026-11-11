from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from app_dnd.models import Character


class SavedCharacterTab(QWidget):
    warning_title = "Aviso"
    changed = Signal(object)
    message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._character: Character | None = None

    def load(self, character: Character | None) -> None:
        self._character = character
        self.setEnabled(character is not None)
        self.refresh()

    def refresh(self) -> None:
        raise NotImplementedError

    def _apply(self, action, message: str = "") -> bool:
        if self._character is None:
            return False
        backup = self._character.model_copy(deep=True)
        try:
            action(self._character)
        except ValueError as exc:
            self._character = backup
            QMessageBox.warning(self, self.warning_title, str(exc))
            self.refresh()
            return False
        self.refresh()
        self.changed.emit(self._character)
        if message:
            self.message.emit(message)
        return True
