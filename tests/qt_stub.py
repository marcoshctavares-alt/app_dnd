from __future__ import annotations

import inspect
import re
import sys
import types

SIGNAL_NAMES = {
    "clicked", "toggled", "stateChanged", "currentIndexChanged", "textChanged", "valueChanged", "currentChanged",
    "itemSelectionChanged", "itemDoubleClicked", "currentRowChanged", "accepted", "rejected", "triggered",
    "editingFinished", "returnPressed", "itemChanged", "currentTextChanged",
}

SIGNAL_PATTERN = re.compile(r"^(\w+Changed|\w+Clicked|\w+Activated|\w+Triggered|finished|selectionChanged)$")


def accepted_args(slot, available):
    try:
        params = list(inspect.signature(slot).parameters.values())
    except (TypeError, ValueError):
        return available
    if any(p.kind is p.VAR_POSITIONAL for p in params):
        return available
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return min(available, len(positional))


class Bound:
    def __init__(self, owner=None):
        self.slots = []
        self.owner = owner

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        if self.owner is not None and self.owner.__dict__.get("_blocked"):
            return
        for slot in list(self.slots):
            slot(*args[: accepted_args(slot, len(args))])


class Signal:
    def __init__(self, *types):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return obj.__dict__.setdefault("_sig_" + self.name, Bound(obj))


class Fake:
    log = []

    def __init__(self, *args, **kwargs):
        self._init_args = args

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name in SIGNAL_NAMES or SIGNAL_PATTERN.match(name):
            bound = Bound(self)
            self.__dict__[name] = bound
            return bound

        def method(*args, **kwargs):
            return Fake()

        return method

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return True


class ConstMeta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return hash(name) & 0xFFFF


class Namespace:
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return hash(name) & 0xFFFF


class QObject(Fake):
    def blockSignals(self, on):
        previous = self.__dict__.get("_blocked", False)
        self._blocked = on
        return previous


SCREEN = [0, 0, 1366, 768]


class Rect:
    def __init__(self, x, y, w, h):
        self._v = (x, y, w, h)

    def x(self):
        return self._v[0]

    def y(self):
        return self._v[1]

    def width(self):
        return self._v[2]

    def height(self):
        return self._v[3]


class Screen:
    def availableGeometry(self):
        return Rect(*SCREEN)


class QGuiApplication(QObject):
    @staticmethod
    def primaryScreen():
        return Screen()

    @staticmethod
    def setHighDpiScaleFactorRoundingPolicy(policy):
        QGuiApplication.policy = policy


class QWidget(QObject):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__()
        self._enabled = True
        self._visible = False
        self._layout = None
        self._size = (640, 480)
        self._min_size = (0, 0)
        self._pos = (0, 0)

    def screen(self):
        return Screen()

    def resizeEvent(self, event):
        pass

    def resize(self, w, h=None):
        self._size = (w, h)

    def width(self):
        return self._size[0]

    def height(self):
        return self._size[1]

    def setMinimumSize(self, w, h):
        self._min_size = (w, h)

    def move(self, x, y=None):
        self._pos = (x, y)

    def setEnabled(self, on):
        self._enabled = on

    def isEnabled(self):
        return self._enabled

    def setLayout(self, layout):
        self._layout = layout


class QLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def clear(self):
        self._text = ""


class QLineEdit(QLabel):
    pass


class QTextEdit(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._text = ""

    def setPlainText(self, text):
        self._text = text

    def toPlainText(self):
        return self._text

    def setText(self, text):
        self._text = text

    def append(self, text):
        self._text += text + "\n"

    def clear(self):
        self._text = ""


class QPlainTextEdit(QTextEdit):
    pass


class QCheckBox(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__()
        self._text, self._checked = text, False

    def isChecked(self):
        return self._checked

    def setChecked(self, on):
        if self._checked != on:
            self._checked = on
            self.toggled.emit(on)

    def text(self):
        return self._text


class QRadioButton(QCheckBox):
    pass


class QPushButton(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__()
        self._text = text

    def text(self):
        return self._text


class QSpinBox(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._value, self._min, self._max = 0, 0, 99

    def setRange(self, lo, hi):
        self._min, self._max = lo, hi
        self._value = max(lo, min(hi, self._value))

    def setMinimum(self, lo):
        self._min = lo
        self._value = max(lo, self._value)

    def setMaximum(self, hi):
        self._max = hi
        self._value = min(hi, self._value)

    def value(self):
        return self._value

    def setValue(self, value):
        value = max(self._min, min(self._max, value))
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)


class QDoubleSpinBox(QSpinBox):
    pass


class QComboBox(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._items, self._index = [], -1

    def addItem(self, text, data=None):
        self._items.append((text, data))
        if self._index < 0:
            self._index = 0

    def clear(self):
        self._items, self._index = [], -1

    def count(self):
        return len(self._items)

    def currentData(self, *args):
        return self._items[self._index][1] if 0 <= self._index < len(self._items) else None

    def currentText(self):
        return self._items[self._index][0] if 0 <= self._index < len(self._items) else ""

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, index):
        if index != self._index and 0 <= index < len(self._items):
            self._index = index
            self.currentIndexChanged.emit(index)

    def findData(self, data, *args):
        for i, (_, d) in enumerate(self._items):
            if d == data:
                return i
        return -1

    def itemData(self, index, *args):
        return self._items[index][1]

    def itemText(self, index):
        return self._items[index][0]



class QListWidgetItem(Fake):
    def __init__(self, text="", *args):
        super().__init__()
        self._text, self._data = text, {}

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def setData(self, role, value):
        self._data[role] = value

    def data(self, role):
        return self._data.get(role)


class QListWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._items, self._row = [], -1

    def addItem(self, item):
        if isinstance(item, str):
            item = QListWidgetItem(item)
        self._items.append(item)

    def clear(self):
        self._items, self._row = [], -1

    def count(self):
        return len(self._items)

    def item(self, row):
        return self._items[row]

    def currentItem(self):
        return self._items[self._row] if 0 <= self._row < len(self._items) else None

    def currentRow(self):
        return self._row

    def setCurrentRow(self, row):
        row = row if 0 <= row < len(self._items) else -1
        changed = row != self._row
        self._row = row
        if changed:
            self.currentItemChanged.emit(self.currentItem(), None)
            self.itemSelectionChanged.emit()

    def setCurrentItem(self, item):
        self.setCurrentRow(self._items.index(item) if item in self._items else -1)

    def selectedItems(self):
        item = self.currentItem()
        return [item] if item else []

    def takeItem(self, row):
        return self._items.pop(row)


class QDialog(QWidget):
    Accepted, Rejected = 1, 0
    exec_result = 0

    def exec(self):
        return type(self).exec_result

    def accept(self):
        pass

    def reject(self):
        pass


class QMessageBox(QWidget):
    Yes, No, Ok, Cancel = 1, 2, 3, 4
    shown = []

    @classmethod
    def warning(cls, parent, title, text, *args):
        cls.shown.append(("warning", title, text))
        return cls.Ok

    @classmethod
    def information(cls, parent, title, text, *args):
        cls.shown.append(("information", title, text))
        return cls.Ok

    @classmethod
    def critical(cls, parent, title, text, *args):
        cls.shown.append(("critical", title, text))
        return cls.Ok

    @classmethod
    def question(cls, parent, title, text, *args):
        cls.shown.append(("question", title, text))
        return cls.Yes


class QFileDialog(QWidget):
    next_open = ("", "")
    next_save = ("", "")

    @classmethod
    def getOpenFileName(cls, *args, **kwargs):
        return cls.next_open

    @classmethod
    def getSaveFileName(cls, *args, **kwargs):
        return cls.next_save


class QInputDialog(QWidget):
    @staticmethod
    def getText(*args, **kwargs):
        return "", False

    answers = []

    @staticmethod
    def getItem(parent, title, label, items, current=0, editable=True):
        if QInputDialog.answers:
            return QInputDialog.answers.pop(0), True
        return items[current], True

    @staticmethod
    def getInt(parent, title, label, value=0, *args, **kwargs):
        return value, True


class QSettings:
    store = {}

    def __init__(self, *args, **kwargs):
        pass

    def value(self, key, default=None, *args, **kwargs):
        return self.store.get(key, default)

    def setValue(self, key, value):
        self.store[key] = value

    def remove(self, key):
        self.store.pop(key, None)


class QMainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._status = Fake()

    def addDockWidget(self, area, dock):
        self.dock_area = area

    def statusBar(self):
        return self

    def showMessage(self, text, *args):
        self.last_status = text

    def menuBar(self):
        return Fake()


class QTabWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._tabs, self._index = [], 0

    def addTab(self, widget, title):
        self._tabs.append((widget, title))

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, index):
        if index != self._index:
            self._index = index
            self.currentChanged.emit(index)

    def currentWidget(self):
        return self._tabs[self._index][0]

    def widget(self, index):
        return self._tabs[index][0]

    def count(self):
        return len(self._tabs)


class QScrollArea(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.inner = None

    def setWidget(self, widget):
        self.inner = widget


class QAction(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.checked = False

    def setCheckable(self, value):
        pass

    def setChecked(self, value):
        self.checked = value

    def isChecked(self):
        return self.checked

    def trigger(self):
        self.checked = True
        self.triggered.emit(True)


class QActionGroup(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.actions = []

    def addAction(self, action):
        self.actions.append(action)


class QApplication(QObject):
    _instance = None

    def __init__(self, *args, **kwargs):
        super().__init__()
        QApplication._instance = self
        self.style_name = "windowsvista"
        self.current_palette = "default-palette"

    @staticmethod
    def instance():
        return QApplication._instance

    def style(self):
        return types.SimpleNamespace(objectName=lambda: self.style_name)

    def setStyle(self, name):
        self.style_name = name

    def palette(self):
        return self.current_palette

    def setPalette(self, palette):
        self.current_palette = palette

    def exec(self):
        return 0


class Namespace2:
    def __getattr__(self, name):
        return name


class QPalette:
    ColorRole = Namespace2()
    ColorGroup = Namespace2()

    def __init__(self):
        self.colors = {}

    def setColor(self, *args):
        self.colors[args[:-1]] = args[-1]


class QColor:
    def __init__(self, value):
        self.value = value


class QPixmap(Fake):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def loadFromData(self, *args, **kwargs):
        return True

    def isNull(self):
        return False

    def scaled(self, *args, **kwargs):
        return self


def build_modules():
    core = types.ModuleType("PySide6.QtCore")
    core.Qt = Namespace()
    core.Signal = Signal
    core.QSettings = QSettings
    core.QObject = QObject
    gui = types.ModuleType("PySide6.QtGui")
    gui.QAction = QAction
    gui.QActionGroup = QActionGroup
    gui.QPalette = QPalette
    gui.QColor = QColor
    gui.QGuiApplication = QGuiApplication
    gui.QPixmap = QPixmap
    widgets = types.ModuleType("PySide6.QtWidgets")
    for name, cls in list(globals().items()):
        if isinstance(cls, type) and name.startswith("Q"):
            setattr(widgets, name, cls)
    widgets.__getattr__ = lambda name: ConstMeta(name, (QWidget,), {}) if name.startswith("Q") else (_ for _ in ()).throw(AttributeError(name))
    gui.__getattr__ = lambda name: ConstMeta(name, (Fake,), {}) if name.startswith("Q") else (_ for _ in ()).throw(AttributeError(name))
    core.__getattr__ = lambda name: ConstMeta(name, (Fake,), {}) if name.startswith("Q") else (_ for _ in ()).throw(AttributeError(name))
    root = types.ModuleType("PySide6")
    root.QtCore, root.QtGui, root.QtWidgets = core, gui, widgets
    return {"PySide6": root, "PySide6.QtCore": core, "PySide6.QtGui": gui, "PySide6.QtWidgets": widgets}


def install():
    modules = build_modules()
    sys.modules.update(modules)
    return modules


def uninstall():
    for name in [n for n in sys.modules if n == "PySide6" or n.startswith("PySide6.") or n.startswith("app_dnd.ui")]:
        del sys.modules[name]
