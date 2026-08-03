@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "ENTRY_POINT=%PROJECT_DIR%src\Main.py"
set "APP_ICON=%PROJECT_DIR%res\ui\app_icon.ico"
set "FACE_DETECTION_MODEL=%PROJECT_DIR%res\ai\insightface\models\buffalo_l\det_10g.onnx"
set "FACE_RECOGNITION_MODEL=%PROJECT_DIR%res\ai\insightface\models\buffalo_l\w600k_r50.onnx"
set "DIST_DIR=%PROJECT_DIR%dist"
set "OUTPUT_DIR=%PROJECT_DIR%dist\OnDeviceAI"
set "BUILD_DIR=%PROJECT_DIR%build"

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found in PATH.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

if not exist "%ENTRY_POINT%" (
    echo [ERROR] Entry point was not found:
    echo         "%ENTRY_POINT%"
    pause
    exit /b 1
)

if not exist "%APP_ICON%" (
    echo [ERROR] Application icon was not found:
    echo         "%APP_ICON%"
    pause
    exit /b 1
)

for %%F in ("%FACE_DETECTION_MODEL%" "%FACE_RECOGNITION_MODEL%") do (
    if not exist "%%~F" (
        echo [ERROR] InsightFace model was not found:
        echo         "%%~F"
        echo         Run git lfs pull before building.
        pause
        exit /b 1
    )
    if %%~zF LSS 1000000 (
        echo [ERROR] InsightFace model is not a valid ONNX file:
        echo         "%%~F"
        echo         Git LFS pointer detected. Run git lfs pull before building.
        pause
        exit /b 1
    )
)

!PYTHON_CMD! -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] PyInstaller is not installed. Installing it now...
    !PYTHON_CMD! -m pip install pyinstaller

    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )

    !PYTHON_CMD! -m PyInstaller --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] PyInstaller was installed but could not be executed.
        pause
        exit /b 1
    )

    echo [OK] PyInstaller installed successfully.
    echo.
)

echo [BUILD] Creating OnDeviceAI.exe...
!PYTHON_CMD! -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --console ^
    --contents-directory _internal ^
    --name OnDeviceAI ^
    --icon "%APP_ICON%" ^
    --paths "%PROJECT_DIR%src" ^
    --hidden-import mediapipe.tasks.c ^
    --collect-binaries mediapipe ^
    --collect-data insightface ^
    --distpath "%DIST_DIR%" ^
    --workpath "%BUILD_DIR%\work" ^
    --specpath "%BUILD_DIR%" ^
    "%ENTRY_POINT%"

if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [COPY] Copying external resources...

if exist "%PROJECT_DIR%config" (
    xcopy "%PROJECT_DIR%config" "%OUTPUT_DIR%\config\" /E /I /Y >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy the config directory.
        pause
        exit /b 1
    )
)

if exist "%PROJECT_DIR%res" (
    xcopy "%PROJECT_DIR%res" "%OUTPUT_DIR%\res\" /E /I /Y >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy the res directory.
        pause
        exit /b 1
    )
)

echo.
echo [SUCCESS] Build completed:
echo           "%OUTPUT_DIR%"
pause
exit /b 0
