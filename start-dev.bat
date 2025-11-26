@echo off
setlocal

echo Starting Backend (tracing disabled)...
start "Backend" cmd /c "set PHOENIX_ENABLED=0& python -m uvicorn api.main:app --port 8000"

echo Starting Frontend...
start "Frontend" cmd /c "cd frontend& set VITE_API_BASE_URL=http://127.0.0.1:8000/api& npm run dev"

echo All services started!
echo Backend API: http://127.0.0.1:8000
echo Frontend: http://localhost:5173

endlocal