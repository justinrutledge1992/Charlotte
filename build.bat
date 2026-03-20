@echo off
echo ============================================================
echo  Charlotte - Build Script
echo ============================================================
echo.

:: Install dependencies
echo Installing dependencies...
pip install pyinstaller beautifulsoup4 lxml requests
echo.

:: Build the executable
echo Building Charlotte.exe...
pyinstaller --onefile --windowed --name "Charlotte" charlotte.py
echo.

echo ============================================================
echo  Build complete!
echo  Your executable is in: dist\Charlotte.exe
echo ============================================================
pause
