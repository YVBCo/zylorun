@echo off
title Unified Security Platform - Complete End-to-End Test Suite
echo ========================================================
echo Running Complete End-to-End Platform & Dashboard E2E Tests...
echo ========================================================
cd /d "%~dp0tester\backend"
"venv\Scripts\python.exe" scripts/run_complete_e2e.py
echo.
echo ========================================================
echo Running Interactive Dashboard & Button Interaction Tests...
echo ========================================================
"venv\Scripts\python.exe" scripts/run_dashboard_and_buttons_e2e.py
echo.
pause
