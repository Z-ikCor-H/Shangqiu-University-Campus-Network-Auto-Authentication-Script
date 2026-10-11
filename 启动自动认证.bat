@echo off
rem 校园网自动认证 —— 每 30 秒检测一次，掉线自动重连
cd /d "%~dp0"
python campus_auth.py --loop 30
pause
