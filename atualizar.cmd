@echo off
rem Dois cliques para atualizar o kit WE no Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0atualizar.ps1" %*
echo.
pause
