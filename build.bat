@echo off
echo =========================================
echo Naver Blog Analyzer EXE Build Start...
echo =========================================
echo 1. Installing requirements...
pip install requests pyinstaller
echo.
echo 2. Building EXE file...
pyinstaller --noconsole --onefile --name "NaverBlogAnalyzer" gui.py
echo.
echo =========================================
echo Build Complete! Check the 'dist' folder.
echo =========================================
pause
