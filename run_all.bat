@echo off
setlocal

echo Starting Phoenix...
start "Phoenix" cmd /c "phoenix serve"

echo Waiting for Phoenix to be ready...
powershell -Command "$max=60;$ok=$false; for($i=0;$i -lt $max;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing http://localhost:6006/; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 1 }; if(-not $ok){Write-Host 'Phoenix not ready after wait'; exit 1 }"

echo Starting Backend...
start "Backend" cmd /c "set PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317& set PHOENIX_PROTOCOL=grpc& set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317& set OTEL_EXPORTER_OTLP_PROTOCOL=grpc& set OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=& python -m uvicorn api.main:app --port 8000"

echo Starting Frontend...
start "Frontend" cmd /c "cd frontend& set VITE_API_BASE_URL=http://127.0.0.1:8000/api& npm run dev"

echo All services started!
echo Phoenix UI: http://localhost:6006
echo Backend API: http://127.0.0.1:8000
echo Frontend: http://localhost:5173

endlocal
