@echo off
setlocal
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8000 .*LISTENING"') do taskkill /pid %%p /f
echo Backend stopped.
