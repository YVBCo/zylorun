@echo off
title Unified Security Platform - Backend API
echo ========================================================
echo Starting Unified FastAPI Backend on http://localhost:8000
echo Swagger UI Docs: http://localhost:8000/docs
echo ========================================================
cd /d "%~dp0"
call "venv\Scripts\activate.bat"
"venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
