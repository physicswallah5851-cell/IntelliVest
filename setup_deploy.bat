@echo off
"C:\Program Files\Git\cmd\git.exe" config --global user.email "deploy@intellivest.app"
"C:\Program Files\Git\cmd\git.exe" config --global user.name "IntelliVest User"
powershell -ExecutionPolicy Bypass -File .\deploy.ps1
