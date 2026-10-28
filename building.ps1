$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Use an isolated interpreter explicitly; activation is not required.
if (!(Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
$buildPython = ".\.venv\Scripts\python.exe"
& $buildPython -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $buildPython -m PyInstaller --noconfirm --onedir --windowed --clean `
    --icon "res/app-icon.ico" `
    --name "VitalsExplorer" `
    --add-data "res/app-icon.ico;res" `
    --add-data "res/app-icon.png;res" `
    --hidden-import sip `
    --hidden-import pytz `
    --hidden-import tzlocal `
    --hidden-import pandas `
    --hidden-import plotly `
    --hidden-import PyQt5.sip `
    --additional-hooks-dir=. `
    --version-file version_info.txt `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
