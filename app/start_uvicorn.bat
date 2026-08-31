@echo off
cd /d C:\Users\elagio\Projects\igame\app_2\app

echo TASK STARTED >> debug_task.txt
echo ==== %date% %time% ==== >> startup_log.txt

call .venv\Scripts\activate.bat
python --version > startup_log.txt 2>&1
where python >> startup_log.txt 2>&1
uvicorn main:app --host 0.0.0.0 --port 8000 >> startup_log.txt 2>&1