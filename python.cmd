@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0runtime\python.exe" (
 "%~dp0runtime\python.exe" -B -X utf8 %*
) else (
 "%~dp0.venv\Scripts\python.exe" -B -X utf8 %*
)
exit /b %errorlevel%
