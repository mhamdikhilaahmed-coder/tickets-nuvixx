
@echo off
setlocal enableextensions enabledelayedexpansion
title Nuvix Suite Pro v2 - Launcher

if not exist ".env" (
    echo [ERROR] .env not found. Copy .env and fill tokens/IDs.
    pause
    exit /b 1
)

call :launch nuvix_ai NUVIX_AI_TOKEN
call :launch nuvix_apps NUVIX_APPS_TOKEN
call :launch nuvix_backup NUVIX_BACKUP_TOKEN
call :launch nuvix_information NUVIX_INFORMATION_TOKEN
call :launch nuvix_invoices NUVIX_INVOICES_TOKEN
call :launch nuvix_machine NUVIX_MACHINE_TOKEN
call :launch nuvix_management NUVIX_MANAGEMENT_TOKEN
call :launch nuvix_sanctions NUVIX_SANCTIONS_TOKEN
call :launch nuvix_system NUVIX_SYSTEM_TOKEN
call :launch nuvix_tickets NUVIX_TICKETS_TOKEN

echo All bots launched (if tokens present). Press any key to close windows individually.
pause
exit /b 0

:launch
set BOT_DIR=%1
set TOKEN_VAR=%2
for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    if /I "%%~A"=="!TOKEN_VAR!" set TOKEN=%%~B
)
if "!TOKEN!"=="" (
    echo Skipping %BOT_DIR% (no token).
    goto :eof
)
start "NUVIX %BOT_DIR%" cmd /c "cd /d %~dp0%BOT_DIR% && python bot.py"
goto :eof
