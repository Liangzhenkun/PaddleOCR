@echo off
setlocal
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "ocr_gui.py"
