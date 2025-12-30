"""
Diagnostic GUI Launcher
Traces exactly when and where TradingSystem is created
"""

import sys
from pathlib import Path

# Monkey-patch TradingSystem to trace creation
original_import = __builtins__.__import__

def traced_import(name, *args, **kwargs):
    """Trace imports"""
    if 'main_cli' in name:
        print(f"🔍 IMPORTING: {name}")
        import traceback
        traceback.print_stack(limit=5)
    return original_import(name, *args, **kwargs)

__builtins__.__import__ = traced_import

# Now run normal launch
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 70)
print("DIAGNOSTIC LAUNCHER - TRACING IMPORTS")
print("=" * 70)
print()

from config.trading_settings import TradingSettingsManager
print("Step 1: Settings loaded")

print("Step 2: Importing GUI...")
from gui.main_window_integrated import main

print("Step 3: Running GUI...")
main()
