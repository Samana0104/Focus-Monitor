@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Always use the libraries.txt next to this batch file.
set "SCRIPT_DIR=%~dp0"
set "LIBRARY_FILE=%SCRIPT_DIR%libraries.txt"

if not exist "%LIBRARY_FILE%" (
    echo [ERROR] libraries.txt was not found.
    echo         Expected path: "%LIBRARY_FILE%"
    pause
    exit /b 1
)

rem Prefer the Python launcher when available, then fall back to python.
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found in PATH.
        echo         Install Python or add it to PATH, then try again.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

echo [INFO] Python: !PYTHON_CMD!
echo [INFO] Package list: "%LIBRARY_FILE%"
echo.

rem Make sure pip is available before processing the list.
!PYTHON_CMD! -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available for the selected Python installation.
    pause
    exit /b 1
)

set /a TOTAL=0
set /a SUCCESS=0
set /a FAILED=0

for /f "usebackq tokens=* delims=" %%L in ("%LIBRARY_FILE%") do (
    set "LIBRARY=%%L"

    rem Trim leading spaces.
    for /f "tokens=*" %%P in ("!LIBRARY!") do set "LIBRARY=%%P"

    rem Ignore empty lines and lines beginning with #.
    if defined LIBRARY if not "!LIBRARY:~0,1!"=="#" (
        set /a TOTAL+=1
        echo [INSTALL] !LIBRARY!
        !PYTHON_CMD! -m pip install "!LIBRARY!"

        if errorlevel 1 (
            echo [FAILED]  !LIBRARY!
            set /a FAILED+=1
        ) else (
            echo [OK]      !LIBRARY!
            set /a SUCCESS+=1
        )
        echo.
    )
)

if !TOTAL! EQU 0 (
    echo [WARN] No libraries were listed in libraries.txt.
) else (
    echo ========================================
    echo Total: !TOTAL!  Success: !SUCCESS!  Failed: !FAILED!
    echo ========================================
)

if !FAILED! GTR 0 (
    echo Some libraries could not be installed.
    pause
    exit /b 1
)

echo Installation completed successfully.
pause
exit /b 0
