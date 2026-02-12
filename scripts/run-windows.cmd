@echo off
REM db-mcp-server Windows 실행 샘플
REM 이 스크립트는 프로젝트 루트에서 실행하세요:  scripts\run-windows.cmd
REM 또는 scripts 폴더에서:  run-windows.cmd

cd /d "%~dp0.."
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo [INFO] .env created from .env.example. Please edit .env with your DB settings.
    )
)

if not exist ".venv" (
    echo [INFO] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Ensure Python 3.10+ is installed.
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

echo [INFO] Starting MCP server (stdio) ...
python -m src.server
