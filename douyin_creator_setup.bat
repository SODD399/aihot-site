@echo off
setlocal
set "ROOT=%~dp0"
set "TOOL_DIR=%ROOT%third_party\douyin-creator-tools"
set "PNPM_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd"

if not exist "%TOOL_DIR%\package.json" (
  echo Cannot find douyin-creator-tools at "%TOOL_DIR%".
  echo Ask Codex to clone https://github.com/wenyg/douyin-creator-tools first.
  pause
  exit /b 1
)

if exist "%PNPM_EXE%" (
  cd /d "%TOOL_DIR%"
  "%PNPM_EXE%" install
  pause
  exit /b %ERRORLEVEL%
)

cd /d "%TOOL_DIR%"
npm install
pause
