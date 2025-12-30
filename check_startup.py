"""
Startup Diagnostic - Check if everything is ready
Run this before launching GUI
"""

import sys
from pathlib import Path

print("="*70)
print("PAIR TRADING SYSTEM - STARTUP DIAGNOSTIC")
print("="*70)
print()

# Add project root
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"📂 Project root: {project_root}")
print(f"🐍 Python version: {sys.version}")
print(f"📍 Working directory: {Path.cwd()}")
print()

# Check dependencies
print("🔍 Checking dependencies...")
print()

missing = []
installed = []

# Required packages
packages = {
    'PyQt6': 'PyQt6',
    'MetaTrader5': 'MetaTrader5',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'scipy': 'scipy',
    'yaml': 'PyYAML',
    'statsmodels': 'statsmodels',
    'arch': 'arch',  # For volatility models
}

for module_name, package_name in packages.items():
    try:
        __import__(module_name)
        print(f"  ✅ {package_name}")
        installed.append(package_name)
    except ImportError:
        print(f"  ❌ {package_name} - MISSING!")
        missing.append(package_name)

print()

# Check project modules
print("🔍 Checking project modules...")
print()

project_errors = []

tests = [
    ("config", "MT5_CONFIG, DATA_CONFIG, INSTRUMENTS"),
    ("models", "HedgeRatioCalculator"),
    ("risk", "PositionSizer, DrawdownMonitor, RiskChecker"),
    ("strategy", "SignalGenerator, OrderManager, PositionTracker"),
    ("core", "DataManager"),
]

for module, items in tests:
    try:
        __import__(module)
        print(f"  ✅ {module} - OK")
    except Exception as e:
        print(f"  ❌ {module} - {e}")
        project_errors.append(f"{module}: {e}")

print()

# Check files exist
print("🔍 Checking critical files...")
print()

critical_files = [
    "config/__init__.py",
    "models/__init__.py",
    "risk/__init__.py",
    "strategy/__init__.py",
    "core/__init__.py",
    "gui/main_window_integrated.py",
    "main_cli.py",
    "launch_gui.py",
]

file_errors = []
for filepath in critical_files:
    full_path = project_root / filepath
    if full_path.exists():
        print(f"  ✅ {filepath}")
    else:
        print(f"  ❌ {filepath} - NOT FOUND!")
        file_errors.append(filepath)

print()
print("="*70)
print("DIAGNOSTIC RESULTS")
print("="*70)
print()

# Summary
all_good = True

if missing:
    all_good = False
    print(f"❌ MISSING DEPENDENCIES ({len(missing)}):")
    for pkg in missing:
        print(f"   - {pkg}")
    print()
    print("   Fix: pip install -r requirements.txt")
    print()

if project_errors:
    all_good = False
    print(f"❌ MODULE ERRORS ({len(project_errors)}):")
    for err in project_errors:
        print(f"   - {err}")
    print()
    print("   Fix: python fix_all_imports.py")
    print()

if file_errors:
    all_good = False
    print(f"❌ MISSING FILES ({len(file_errors)}):")
    for f in file_errors:
        print(f"   - {f}")
    print()
    print("   Fix: Re-extract package")
    print()

if all_good:
    print("✅ ALL CHECKS PASSED!")
    print()
    print("🚀 Ready to launch GUI:")
    print("   python launch_gui.py")
else:
    print("⚠️  PLEASE FIX ISSUES ABOVE BEFORE LAUNCHING")
    print()
    print("Quick fixes:")
    print("  1. pip install -r requirements.txt")
    print("  2. python fix_all_imports.py")
    print("  3. python check_startup.py  (run this again)")

print()
print("="*70)

sys.exit(0 if all_good else 1)
