@echo off
title MAESTRO - Master Multi-Engine Production Launcher
color 0b

echo ==============================================================================
echo       MAESTRO - LAUNCHING ALL MULTI-AI ENGINES (FULL PRODUCTION SUITE)
echo ==============================================================================
echo.
echo  Starting all 6 background services in separate dedicated windows:
echo   [1] MAESTRO Backend + App Suite        -> http://127.0.0.1:8765
echo   [2] Ollama Local AI Brain Server       -> http://127.0.0.1:11434
echo   [3] ComfyUI NVIDIA RTX GPU Engine      -> http://127.0.0.1:8188
echo   [4] MoneyPrinterTurbo API Engine       -> http://127.0.0.1:8080
echo   [5] MoneyPrinterTurbo Web Studio       -> http://127.0.0.1:8501
echo   [6] Vite Frontend Dev Server (Live UI) -> http://localhost:5173
echo.
echo ==============================================================================

rem 1. MAESTRO Backend
start "MAESTRO Suite [Port 8765]" cmd /k "cd /d %~dp001_main_app && color 0A && echo [1/6] MAESTRO Backend starting on http://127.0.0.1:8765 ... && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"

rem 2. Ollama Server
start "Ollama Brain Server [Port 11434]" cmd /k "color 0E && echo [2/6] Ollama Server starting on http://127.0.0.1:11434 ... && ollama serve"

rem 3. ComfyUI Engine
if exist "C:\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\python_embeded\python.exe" (
    start "ComfyUI GPU Engine [Port 8188]" cmd /k "cd /d C:\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable && color 0D && echo [3/6] ComfyUI starting on http://127.0.0.1:8188 ... && .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build"
) else (
    echo [Warning] ComfyUI directory not found at C:\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable.
)

rem 4. MoneyPrinterTurbo API
if exist "C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\api.bat" (
    start "MoneyPrinterTurbo API [Port 8080]" cmd /k "cd /d C:\MoneyPrinterTurbo-Portable-Windows-1.3.0 && color 0B && echo [4/6] MoneyPrinterTurbo API starting on port 8080 ... && api.bat"
) else (
    echo [Warning] MoneyPrinterTurbo API not found at C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\api.bat.
)

rem 5. MoneyPrinterTurbo Web
if exist "C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\start.bat" (
    start "MoneyPrinterTurbo Web [Port 8501]" cmd /k "cd /d C:\MoneyPrinterTurbo-Portable-Windows-1.3.0 && color 0C && echo [5/6] MoneyPrinterTurbo Web starting on port 8501 ... && start.bat"
) else (
    echo [Warning] MoneyPrinterTurbo Web not found at C:\MoneyPrinterTurbo-Portable-Windows-1.3.0\start.bat.
)

rem 6. Vite Frontend Live Dev Server
start "Vite UI Dev Server [Port 5173]" cmd /k "cd /d %~dp001_main_app\frontend_v2 && color 09 && echo [6/6] Vite Frontend Live UI starting on http://localhost:5173 ... && npm run dev"

echo.
echo ==============================================================================
echo  ALL ENGINES LAUNCHED SUCCESSFULLY!
echo  Open your browser to: http://127.0.0.1:8765 (Production) or http://localhost:5173 (Dev)
echo ==============================================================================
timeout /t 5 >nul
