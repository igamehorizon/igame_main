@echo off
cd /d C:\Users\elagio\Downloads\i-game\app_2\app
call .venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000