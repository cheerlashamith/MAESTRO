@echo off
title MAESTRO YouTube Channel Linker
color 0a

echo ==============================================================================
echo       MAESTRO - CONNECT YOUR YOUTUBE CHANNEL (1-CLICK SETUP)
echo ==============================================================================
echo.
echo  This tool will open Google Sign-in in your default browser.
echo  Log into the Google account that manages your YouTube channel,
echo  click "Allow" to grant MAESTRO upload and analytics permissions,
echo  and MAESTRO will automatically save your permanent login token!
echo.
echo  Press any key to open the Google Authorization page...
echo ==============================================================================
pause >nul

python connect_youtube_account.py

echo.
echo ==============================================================================
echo  Press any key to exit...
pause >nul
