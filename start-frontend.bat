@echo off
title Unified Security Platform - Frontend
echo ========================================================
echo Starting Unified Vite Frontend on http://localhost:5173
echo ========================================================
cd /d "%~dp0tester\frontend"
call npm.cmd run dev
pause
