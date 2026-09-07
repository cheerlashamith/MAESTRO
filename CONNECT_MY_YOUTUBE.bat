@echo off
title MAESTRO YouTube Channel Linker
color 0a

echo ==============================================================================
echo       MAESTRO - CONNECT YOUR YOUTUBE CHANNEL (1-CLICK SETUP)
echo ==============================================================================
echo.
echo  This tool connects MAESTRO to your YouTube account for automated 24/7
echo  video uploads, telemetry-driven SEO, and passive income generation.
echo.
cd 01_main_app
python connect_youtube_account.py
cd ..

echo.
echo ==============================================================================
echo  Press any key to exit...
pause >nul
