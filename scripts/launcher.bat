@echo off
setlocal

REM ============================================
REM CareerAI Assistant - Launcher
REM Lives in /scripts, so we go one level up to reach the project root.
REM Builds the frontend automatically before launching, so it always
REM reflects the latest code instead of a stale .exe.
REM ============================================

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set BACKEND_DIR=%ROOT_DIR%\backend
set FRONTEND_DIR=%ROOT_DIR%\frontend

echo Starting CareerAI Assistant...
echo.

REM --- Kill any leftover frontend.exe so the build isn't blocked by a file lock ---
echo [0/3] Closing any previous instance...
taskkill /IM frontend.exe /F >nul 2>&1
timeout /t 1 /nobreak >nul

REM --- Start backend in a new window ---
echo [1/3] Starting backend (FastAPI)...
start "CareerAI Backend" cmd /k "cd /d %BACKEND_DIR% && .venv\Scripts\python.exe main.py"

REM --- Build frontend so we always run the latest code ---
echo [2/3] Building frontend (this keeps the app up to date)...
pushd "%FRONTEND_DIR%"
dotnet build -c Debug --nologo
set BUILD_RESULT=%ERRORLEVEL%
popd

if not %BUILD_RESULT%==0 (
    echo.
    echo Frontend build failed. See errors above.
    echo The backend window is still running in the background if you need it.
    pause
    exit /b 1
)

REM --- Wait a moment so the backend has time to boot before frontend connects ---
timeout /t 3 /nobreak >nul

REM --- Start frontend ---
echo [3/3] Starting frontend (WPF)...

set EXE_PATH=%FRONTEND_DIR%\bin\Debug\net10.0-windows\frontend.exe

if exist "%EXE_PATH%" (
    start "" "%EXE_PATH%"
) else (
    echo.
    echo Could not find frontend.exe at:
    echo   %EXE_PATH%
    echo.
    echo The build reported success but the exe wasn't found there.
    echo Check that the target framework folder name matches ^(e.g. net10.0-windows^).
    pause
    exit /b 1
)

echo.
echo Both processes started. The backend window will stay open with logs -
echo close it manually when you're done, or closing it will stop the API.
echo.
