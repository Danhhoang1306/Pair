"""
SIMPLE FIX - Just add models to path
Run this if you get "No module named 'models'" error
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("="*70)
print("QUICK PATH FIX")
print("="*70)
print(f"Added to Python path: {project_root}")
print()

# Test imports
print("Testing imports...")
errors = []

try:
    from config import MT5_CONFIG
    print("✅ config - OK")
except Exception as e:
    print(f"❌ config - {e}")
    errors.append(str(e))

try:
    from models import HedgeRatioCalculator
    print("✅ models - OK")
except Exception as e:
    print(f"❌ models - {e}")
    errors.append(str(e))

try:
    from risk import PositionSizer
    print("✅ risk - OK")
except Exception as e:
    print(f"❌ risk - {e}")
    errors.append(str(e))

try:
    from strategy import SignalGenerator
    print("✅ strategy - OK")
except Exception as e:
    print(f"❌ strategy - {e}")
    errors.append(str(e))

print()
if errors:
    print("⚠️  Some imports failed. Run: python fix_all_imports.py")
    print("   Or install missing dependencies: pip install -r requirements.txt")
else:
    print("✅ All imports working!")
    print()
    print("Now run: python launch_gui.py")

print("="*70)
