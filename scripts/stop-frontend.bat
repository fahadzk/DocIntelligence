@echo off
setlocal
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5173 .*LISTENING"') do taskkill /pid %%p /f
echo Frontend stopped.
