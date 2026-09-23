@echo off
setlocal
cd /d "%~dp0.."
start "Document Intelligence Frontend" cmd /k "npm.cmd run dev:frontend"
