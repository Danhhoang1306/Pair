# ==========================================
# Pair Trading System - PowerShell Launcher
# ==========================================

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Pair Trading System - Professional Edition" -ForegroundColor White
Write-Host "  PowerShell Launcher" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
$currentPath = Get-Location
Write-Host "Current directory: $currentPath" -ForegroundColor Yellow

# Check for required files
$requiredFiles = @(
    "launch_gui.py",
    "main_cli.py",
    "config\trading_settings.yaml",
    "assets\darcula_theme.css"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "[OK] Found: $file" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Missing: $file" -ForegroundColor Red
        $allFilesExist = $false
    }
}

Write-Host ""

if (-not $allFilesExist) {
    Write-Host "ERROR: Some required files are missing!" -ForegroundColor Red
    Write-Host "Please make sure you're in the pair_trading_pro directory." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Current files in directory:" -ForegroundColor Yellow
    Get-ChildItem -Name | Select-Object -First 10
    Write-Host ""
    pause
    exit 1
}

# Check for Python
Write-Host "Checking Python installation..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ and add to PATH" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""

# Check for venv
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "[OK] Virtual environment found" -ForegroundColor Green
    $pythonExe = "venv\Scripts\python.exe"
} else {
    Write-Host "[WARNING] Virtual environment not found, using system Python" -ForegroundColor Yellow
    $pythonExe = "python"
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Starting GUI..." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Launch the GUI
try {
    & $pythonExe launch_gui.py
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to start GUI!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}
