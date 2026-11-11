#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[ui,pdf]" pyinstaller
pyinstaller packaging/app_dnd.spec --noconfirm --clean
case "$(uname -s)" in
  Darwin) exe="dist/APP_DND.app/Contents/MacOS/APP_DND" ;;
  *) exe="dist/APP_DND/APP_DND" ;;
esac
"$exe" --selftest
echo "Pronto: dist/APP_DND"
