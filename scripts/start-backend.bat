@echo off
setlocal
cd /d "%~dp0.."

:: Set the environment variable inside the new cmd window
start "Document Intelligence Backend" cmd /k "set DEBUGGER=true&& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend --workers 1"
