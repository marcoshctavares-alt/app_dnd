@echo off
setlocal
cd /d "%~dp0\.."
python -m venv .build-venv || exit /b 1
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip || exit /b 1
pip install -e ".[ui,pdf]" pyinstaller || exit /b 1
pyinstaller packaging\app_dnd.spec --noconfirm --clean || exit /b 1
start /wait "" dist\APP_DND\APP_DND.exe --selftest=dist\selftest.txt
type dist\selftest.txt
echo Pronto: dist\APP_DND  (compacte a pasta em ZIP para enviar)
