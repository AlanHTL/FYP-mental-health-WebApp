@echo off
set API_KEY=sk-UnNXXoNG6qqa1RUl24zKrakQaHBeyxqkxEtaVwGbSrGlRQxl
set API_BASE=https://xiaoai.plus/v1
echo Starting the server...
echo API_KEY and API_BASE are set
call .venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload