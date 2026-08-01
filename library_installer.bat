@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LIBRARY_FILE=%SCRIPT_DIR%libraries.txt"
set "REINSTALL=0"
set "NO_PAUSE=0"

for %%A in (%*) do (
    if /I "%%~A"=="--reinstall" set "REINSTALL=1"
    if /I "%%~A"=="--no-pause" set "NO_PAUSE=1"
)

if not exist "%LIBRARY_FILE%" (
    echo [ERROR] libraries.txt was not found.
    echo         Expected path: "%LIBRARY_FILE%"
    call :pause_if_needed
    exit /b 1
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found in PATH.
        call :pause_if_needed
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

echo [INFO] Python: !PYTHON_CMD!
!PYTHON_CMD! -c "import sys; print('[INFO] Python executable:', sys.executable)"
echo [INFO] Package list: "%LIBRARY_FILE%"
echo.

!PYTHON_CMD! -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available for the selected Python installation.
    call :pause_if_needed
    exit /b 1
)

if "!REINSTALL!"=="0" (
    choice /C YN /N /M "Uninstall and reinstall all libraries? [Y/N]: "
    if errorlevel 2 (
        set "REINSTALL=0"
    ) else (
        set "REINSTALL=1"
    )
    echo.
)

if "!REINSTALL!"=="1" (
    echo [UNINSTALL] Removing packages from libraries.txt...
    !PYTHON_CMD! -m pip uninstall -y -r "%LIBRARY_FILE%"
    echo [UNINSTALL] Removing AI runtime variants...
    !PYTHON_CMD! -m pip uninstall -y torch torchvision torchaudio onnxruntime onnxruntime-gpu
    echo.
)

set /a TOTAL=0
set /a SUCCESS=0
set /a FAILED=0

for /f "usebackq tokens=* delims=" %%L in ("%LIBRARY_FILE%") do (
    set "LIBRARY=%%L"
    for /f "tokens=*" %%P in ("!LIBRARY!") do set "LIBRARY=%%P"

    if defined LIBRARY if not "!LIBRARY:~0,1!"=="#" (
        set /a TOTAL+=1
        echo [INSTALL] !LIBRARY!
        !PYTHON_CMD! -m pip install "!LIBRARY!"

        if errorlevel 1 (
            echo [FAILED] !LIBRARY!
            set /a FAILED+=1
        ) else (
            echo [OK] !LIBRARY!
            set /a SUCCESS+=1
        )
        echo.
    )
)

if !FAILED! GTR 0 (
    echo [ERROR] One or more common libraries failed to install.
    call :pause_if_needed
    exit /b 1
)

where nvidia-smi >nul 2>&1
if errorlevel 1 goto install_cpu_runtime

:install_gpu_runtime
if "!REINSTALL!"=="0" (
    !PYTHON_CMD! -c "import torch, onnxruntime as ort; assert torch.cuda.is_available(); assert 'CUDAExecutionProvider' in ort.get_available_providers(); print('[OK] Existing GPU runtime:', torch.cuda.get_device_name(0)); print('[OK] Torch CUDA:', torch.version.cuda); print('[OK] ONNX providers:', ort.get_available_providers())"
    if not errorlevel 1 goto install_complete
)

echo [GPU] NVIDIA GPU detected. Installing CUDA 13.2 AI runtimes...
!PYTHON_CMD! -m pip uninstall -y torch torchvision torchaudio onnxruntime onnxruntime-gpu >nul 2>&1
!PYTHON_CMD! -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu132
if errorlevel 1 goto runtime_install_failed

!PYTHON_CMD! -m pip install --upgrade onnxruntime-gpu
if errorlevel 1 goto runtime_install_failed

!PYTHON_CMD! -c "import torch, onnxruntime as ort; assert torch.cuda.is_available(), 'PyTorch CUDA is unavailable'; assert 'CUDAExecutionProvider' in ort.get_available_providers(), 'ONNX CUDA provider is unavailable'; print('[OK] GPU:', torch.cuda.get_device_name(0)); print('[OK] Torch CUDA:', torch.version.cuda); print('[OK] ONNX providers:', ort.get_available_providers())"
if errorlevel 1 goto runtime_install_failed
goto install_complete

:install_cpu_runtime
if "!REINSTALL!"=="0" (
    !PYTHON_CMD! -c "import torch, onnxruntime as ort; assert 'CPUExecutionProvider' in ort.get_available_providers(); print('[OK] Existing CPU runtime'); print('[OK] ONNX providers:', ort.get_available_providers())"
    if not errorlevel 1 goto install_complete
)

echo [CPU] NVIDIA GPU was not detected. Installing CPU AI runtimes...
!PYTHON_CMD! -m pip uninstall -y onnxruntime-gpu >nul 2>&1
!PYTHON_CMD! -m pip install --upgrade torch torchvision onnxruntime
if errorlevel 1 goto runtime_install_failed

!PYTHON_CMD! -c "import torch, onnxruntime as ort; print('[OK] Torch device: CPU'); print('[OK] ONNX providers:', ort.get_available_providers())"
if errorlevel 1 goto runtime_install_failed
goto install_complete

:runtime_install_failed
echo [ERROR] Failed to install or verify the AI runtime.
call :pause_if_needed
exit /b 1

:install_complete
echo.
echo ========================================
echo Common packages: !TOTAL!  Success: !SUCCESS!  Failed: !FAILED!
echo ========================================
echo Installation completed successfully.
call :pause_if_needed
exit /b 0

:pause_if_needed
if "!NO_PAUSE!"=="0" pause
exit /b 0
