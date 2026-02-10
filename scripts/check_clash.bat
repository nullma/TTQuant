@echo off
echo ========================================
echo Clash Proxy Diagnostic Tool
echo ========================================
echo.

echo [1] Checking Clash processes...
tasklist | findstr /I "clash verge"
echo.

echo [2] Checking listening ports...
netstat -ano | findstr "LISTENING" | findstr "7890 7891 1080 10808 10809"
echo.

echo [3] Testing proxy ports...
for %%p in (7890 7891 1080 10808 10809) do (
    echo Testing port %%p...
    curl -x http://127.0.0.1:%%p --connect-timeout 2 https://www.google.com -I 2^>nul
    if errorlevel 1 (
        echo   Port %%p: FAILED
    ) else (
        echo   Port %%p: OK
    )
)
echo.

echo [4] Checking Clash config location...
if exist "%USERPROFILE%\.config\clash" (
    echo   Found: %USERPROFILE%\.config\clash
)
if exist "%USERPROFILE%\.config\clash-verge" (
    echo   Found: %USERPROFILE%\.config\clash-verge
)
if exist "%APPDATA%\clash-verge" (
    echo   Found: %APPDATA%\clash-verge
)
echo.

echo ========================================
echo Next Steps:
echo ========================================
echo 1. Open Clash Verge
echo 2. Settings ^> Allow LAN (允许局域网连接)
echo 3. Check proxy port in Settings
echo 4. Run this script again to verify
echo ========================================
pause
