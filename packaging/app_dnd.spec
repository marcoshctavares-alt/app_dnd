# PyInstaller spec: pyinstaller packaging/app_dnd.spec --noconfirm --clean
import sys
from pathlib import Path

root = Path(SPECPATH).parent
data_dir = root / "src" / "app_dnd" / "data"
datas = [(str(p), "app_dnd/data") for p in sorted(data_dir.glob("*.json"))]

a = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root / "src")],
    datas=datas,
    hiddenimports=["PIL.Image", "pypdf"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="APP_DND",
    console=False,
    icon=str(root / "packaging" / "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="APP_DND")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="APP_DND.app", bundle_identifier="local.app-dnd")
