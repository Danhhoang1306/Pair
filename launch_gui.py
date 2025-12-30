"""
Pair Trading System - GUI Launcher
Launch the professional trading interface with full integration
"""

import sys
from pathlib import Path

# Add project root to path (CRITICAL for imports to work)
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Verify path is set
print(f"Project root: {project_root}")
print(f"Python path: {sys.path[0]}")
print("")

# CRITICAL: Initialize configuration BEFORE GUI
# This ensures all settings are loaded from file (if exists)
# BEFORE any GUI components are created
print("="*70)
print("  Pair Trading System - Professional Edition")
print("  Fully Integrated GUI with Trading Logic")
print("="*70)
print("")

# Step 1: Initialize simplified settings system
from config.trading_settings import TradingSettingsManager
print("🔧 Step 1: Loading Trading Settings...")
settings_manager = TradingSettingsManager()  # This will load from file or create defaults
print("")

# Step 2: Launch GUI with loaded configuration
print("🎨 Step 2: Starting GUI...")
from gui.main_window_integrated import main

if __name__ == "__main__":
    main()

