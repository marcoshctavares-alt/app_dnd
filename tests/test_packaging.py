import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spec_bundles_all_json_data_by_glob():
    spec = (ROOT / "packaging" / "app_dnd.spec").read_text(encoding="utf-8")
    assert '.glob("*.json")' in spec and '"app_dnd/data"' in spec
    assert list((ROOT / "src" / "app_dnd" / "data").glob("*.json"))


def test_launcher_and_scripts_exist():
    launcher = (ROOT / "packaging" / "launcher.py").read_text(encoding="utf-8")
    assert "from app_dnd.ui.app import main" in launcher
    for name in ("build.sh", "build.bat", "app_dnd.spec"):
        assert (ROOT / "packaging" / name).is_file()
    assert re.search(r"--selftest", (ROOT / "packaging" / "build.sh").read_text())


def test_entrypoint_supports_selftest_flag():
    source = (ROOT / "src" / "app_dnd" / "ui" / "app.py").read_text(encoding="utf-8")
    assert "--selftest" in source and "def selftest" in source


def test_requirements_cover_runtime_dependencies():
    names = {line.split(">")[0].strip().lower() for line in (ROOT / "requirements.txt").read_text().splitlines() if line}
    assert {"pydantic", "pyside6", "pypdf", "pillow"} <= names
    assert "pyinstaller" in (ROOT / "requirements-build.txt").read_text().lower()


def test_icon_is_a_valid_multi_size_ico():
    from PIL import Image

    icon = Image.open(ROOT / "packaging" / "icon.ico")
    assert icon.format == "ICO" and {(16, 16), (32, 32), (256, 256)} <= set(icon.info["sizes"])


def test_onefile_script_adds_every_data_json_and_icon():
    script = (ROOT / "packaging" / "build_onefile.bat").read_text()
    assert "--onefile" in script and "--windowed" in script and "app_dnd/data" in script
    assert "icon.ico" in script and "--selftest" in script


def test_data_files_load_without_source_checkout_paths():
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "app_dnd").rglob("*.py"))
    assert "__file__" not in source and "_MEIPASS" not in source


def test_license_file_is_gpl3_and_declared_in_metadata():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("                    GNU GENERAL PUBLIC LICENSE") and "Version 3, 29 June 2007" in text
    assert "GPL-3.0-or-later" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_credits_dialog_mentions_program_license_and_srd_attribution():
    from app_dnd.data.credits import ATTRIBUTION, CONTENT_NOTE, LICENSE_NOTE

    assert "Marcos Tavares" in LICENSE_NOTE and "GPL" in LICENSE_NOTE and "CC BY 4.0" in LICENSE_NOTE
    assert "Creative Commons" in ATTRIBUTION and "não são oficiais" in CONTENT_NOTE
