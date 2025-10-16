@echo off
echo Starting Astro Web App...

REM Start React frontend
cd C:\Users\olsen\Documents\astro-frontend
start cmd /k "npm run dev"

REM Start ngrok
cd C:\Users\olsen
start cmd /k "ngrok start --all"

REM Start FastAPI backend
cd C:\Users\olsen\Documents\astro-backend
start cmd /k "conda activate base && uvicorn main:app --host 0.0.0.0 --port 8000"

echo All services started in separate windows.
pause
