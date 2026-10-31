@echo off
setlocal
cd /d "%~dp0"
call "%~dp0python.cmd" "%~dp0vendor\mtkclient\mtk.py" %*
exit /b %errorlevel%
