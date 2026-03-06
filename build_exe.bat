@echo off
echo Packaging CASI Agent into a standalone Windows Executable...

:: Ensure pyinstaller is installed
python -m pip install -r requirements.txt

:: Clean up old builds
rmdir /s /q build
rmdir /s /q dist

:: Build the executable
:: --noconsole hides the cmd window (required for background agent)
:: --icon adds our branding icon
:: --add-data includes the icon file inside the exe package
python -m PyInstaller --noconsole --onefile --icon=casi_icon.ico --add-data "casi_icon.ico;." casi_agent.py

echo Done!
echo The lightweight executable is located at c:\CASI_agent\dist\casi_agent.exe
echo To run it at startup, create a shortcut to it and place it in shell:startup
