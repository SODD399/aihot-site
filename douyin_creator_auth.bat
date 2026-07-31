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

if not exist "%TOOL_DIR%\node_modules" (
  echo Dependencies are not installed. Run douyin_creator_setup.bat first.
  pause
  exit /b 1
)

cd /d "%TOOL_DIR%"
if exist "%PNPM_EXE%" (
  "%PNPM_EXE%" run auth
) else (
  npm run auth
)
pause
