@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\.."
python -m venv .build-venv || exit /b 1
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip || exit /b 1
pip install -r requirements-build.txt || exit /b 1
set ADD=
for %%f in (src\app_dnd\data\*.json) do set ADD=!ADD! --add-data "%%f;app_dnd/data"
pyinstaller --onefile --windowed --noconfirm --clean --name "FichasDnD" --icon packaging\icon.ico --paths src --collect-all PySide6 !ADD! packaging\launcher.py || exit /b 1
start /wait "" dist\FichasDnD.exe --selftest=dist\selftest.txt
type dist\selftest.txt
for %%f in (dist\FichasDnD.exe) do echo Tamanho: %%~zf bytes
echo Pronto: dist\FichasDnD.exe
