@echo off
title MAESTRO 24/7 Autonomous YouTube Director
color 0b

echo ==============================================================================
echo       MAESTRO 24/7 AUTONOMOUS YOUTUBE DIRECTOR (LOCAL LAPTOP RUNNER)
echo ==============================================================================
echo.
echo  [IMPORTANT LAPTOP SETTINGS FOR 24/7 OPERATION WITH LID CLOSED]:
echo  1. Open Windows Control Panel -> Power Options
echo  2. Click "Choose what closing the lid does"
echo  3. Under "When I close the lid" -> Set BOTH to "Do nothing"
echo  4. Keep your laptop connected to its power adapter and Wi-Fi.
echo  5. You can now close the laptop lid! The screen turns off, but MAESTRO
echo     continues generating videos, reading comments, and publishing 24/7!
echo.
echo ==============================================================================
echo  Starting Autonomous Daemon Loop (Auto-restarts on any error)...
echo ==============================================================================

:daemon_loop
python run_autonomous_daemon.py
echo [!] Daemon process exited at %date% %time%. Restarting in 15 seconds...
timeout /t 15 /nobreak >nul
goto daemon_loop
