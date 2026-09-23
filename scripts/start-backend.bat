@echo off
setlocal
cd /d "%~dp0.."
start "Document Intelligence Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend"
