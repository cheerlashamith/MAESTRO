@echo off
title MAESTRO - Multi-Agent Autonomous Engine for Scalable Transmedia Production & Orchestration
color 0B

echo ===============================================================================
echo   MAESTRO - MULTI-AGENT AUTONOMOUS TRANSMEDIA PRODUCTION & ORCHESTRATION
echo ===============================================================================
echo.
echo Select how you want to run MAESTRO:
echo.
echo  [1] STANDARD MODE (Recommended - Only 1 Command Prompt needed)
echo      - Runs AutoCourse Backend + Frontend (built) on http://127.0.0.1:8765
echo      - Uses built-in Direct Neural Synthesizer, Edge-TTS, and Manim.
echo      - No other windows needed!
echo.
echo  [2] FULL AI SUITE (Opens 3 Windows)
echo      - Window 1: AutoCourse Main App (Port 8765)
echo      - Window 2: MoneyPrinterTurbo API Engine (Port 8080)
echo      - Window 3: ComfyUI Engine (Port 8188)
echo.
echo  [3] FRONTEND DEV MODE (For editing UI code)
echo      - Window 1: FastAPI Backend (Port 8765)
echo      - Window 2: Vite Hot-Reloading Dev Server (Port 5173)
echo.
echo  [4] EXIT
echo.
echo ===============================================================================
set /p choice="Enter your choice [1-4] (Default is 1): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto standard
if "%choice%"=="2" goto full_suite
if "%choice%"=="3" goto dev_mode
if "%choice%"=="4" goto end
goto standard

:standard
echo.
echo Starting AutoCourse Main App (Backend + Frontend)...
cd /d "%~dp001_main_app"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
pause
goto end

:full_suite
echo.
echo Launching Full AI Suite in separate command prompts...

rem Window 1: AutoCourse Main App
start "[AutoCourse 1/3] Main App (Port 8765)" cmd /k "cd /d %~dp001_main_app && color 0A && echo Starting AutoCourse Backend + Frontend on http://127.0.0.1:8765 ... && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"

rem Window 2: MoneyPrinterTurbo API
if exist "C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\api.bat" (
    start "[AutoCourse 2/3] MoneyPrinterTurbo API (Port 8080)" cmd /k "cd /d C:\MoneyPrinterTurbo-Portable-Windows-1.3.0 && color 0E && echo Starting MoneyPrinterTurbo API on port 8080... && api.bat"
) else (
    echo [Warning] C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\api.bat not found. Skipping MPT.
)

rem Window 3: ComfyUI Engine
if exist "C:\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\run_nvidia_gpu.bat" (
    start "[AutoCourse 3/3] ComfyUI Engine (Port 8188)" cmd /k "cd /d C:\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable && color 0D && echo Starting ComfyUI on port 8188... && run_nvidia_gpu.bat"
) else (
    echo [Warning] ComfyUI run_nvidia_gpu.bat not found. Skipping ComfyUI.
)

echo.
echo All requested engines have been launched in their own command prompts!
echo Open your browser to: http://127.0.0.1:8765
echo.
pause
goto end

:dev_mode
echo.
echo Launching Developer Mode...
start "[Dev 1/2] FastAPI Backend" cmd /k "cd /d %~dp001_main_app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload"
start "[Dev 2/2] Vite UI Dev Server" cmd /k "cd /d %~dp001_main_app\frontend_v2 && npm run dev"
goto end

:end
