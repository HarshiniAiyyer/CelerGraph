@echo off
echo Starting backend and frontend servers...

REM Start FastAPI backend
echo Starting FastAPI server...
start "Backend" cmd /k "cd /d d:\inco && python -m uvicorn api.main:app --reload --port 8000"

REM Start Vite frontend
echo Starting frontend dev server...
start "Frontend" cmd /k "cd /d d:\inco\frontend && npm run dev"

echo Both servers are starting in new windows.