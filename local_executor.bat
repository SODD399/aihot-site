@echo off
setlocal
set "ROOT=%~dp0"
set "NODE_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
set "NODE_PATH=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

if not exist "%NODE_EXE%" (
  echo Cannot find bundled Node.js at "%NODE_EXE%".
  echo Install Node.js and Playwright, or run this from Codex where the bundled runtime exists.
  exit /b 1
)

"%NODE_EXE%" "%ROOT%local_executor.js" %*
