@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_pipeline.ps1" %*
if errorlevel 1 (
  echo AAVE pipeline failed.
  exit /b 1
)

echo AAVE pipeline completed.
exit /b 0
