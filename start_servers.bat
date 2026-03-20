@echo off
TITLE AI Exam Startup Script
echo ==============================================
echo 🚀 STARTING AI EXAM LOCAL ENVIRONMENT 🚀
echo ==============================================

echo [1/2] Launching Django Backend (Port 8000)...
start "AI Exam Backend (Django)" cmd /k "cd /d %~dp0 && title AI Exam Backend (Port 8000) && py manage.py runserver 8000"

echo [2/2] Launching React Frontend (Port 5173)...
start "AI Exam Frontend (React/Vite)" cmd /k "cd /d %~dp0frontend && title AI Exam Frontend (Port 5173) && npm run dev"

echo.
echo ==============================================
echo ✅ SERVERS ARE LAUNCHING IN NEW WINDOWS! ✅
echo ==============================================
echo - Your Django Database is at: http://127.0.0.1:8000/admin/
echo - Your React App is at:       http://localhost:5173/
echo.
echo Please leave those black command windows open.
pause
