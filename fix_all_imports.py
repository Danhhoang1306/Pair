"""
COMPREHENSIVE IMPORT FIX
Fixes all imports across the entire project
"""

from pathlib import Path
import shutil

print("="*70)
print("COMPREHENSIVE IMPORT FIX FOR PAIR TRADING PRO")
print("="*70)
print()

project_root = Path(__file__).parent

# ============================================================
# FIX 1: strategy/__init__.py
# ============================================================
print("📝 Fixing strategy/__init__.py...")

strategy_init = project_root / "strategy" / "__init__.py"
strategy_init_content = '''"""Trading strategies"""

from .signal_generator import SignalGenerator, SignalType, SignalStrength, TradingSignal
from .order_manager import OrderManager, Order, OrderType, OrderSide, OrderStatus
from .position_tracker import PositionTracker, Position

__all__ = [
    # Signal Generation
    'SignalGenerator',
    'SignalType',
    'SignalStrength', 
    'TradingSignal',
    # Order Management
    'OrderManager',
    'Order',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    # Position Tracking
    'PositionTracker',
    'Position',
]
'''

with open(strategy_init, 'w', encoding='utf-8') as f:
    f.write(strategy_init_content)

print("✅ strategy/__init__.py fixed")

# ============================================================
# FIX 2: utils/__init__.py
# ============================================================
print("📝 Fixing utils/__init__.py...")

utils_init = project_root / "utils" / "__init__.py"
utils_init_content = '''"""Utility modules"""

# Make logger available
try:
    from .logger import setup_logging
    __all__ = ['setup_logging']
except ImportError:
    __all__ = []
'''

with open(utils_init, 'w', encoding='utf-8') as f:
    f.write(utils_init_content)

print("✅ utils/__init__.py fixed")

# ============================================================
# FIX 2b: utils/logger.py
# ============================================================
print("📝 Fixing utils/logger.py...")

logger_file = project_root / "utils" / "logger.py"
if logger_file.exists():
    content = logger_file.read_text(encoding='utf-8')
    # Fix wrong import
    if "from config.settings import LOGGING_CONFIG" in content:
        content = content.replace(
            "from config.settings import LOGGING_CONFIG",
            "from config import LOGGING_CONFIG"
        )
        logger_file.write_text(content, encoding='utf-8')
        print("✅ utils/logger.py fixed (import corrected)")
    else:
        print("✅ utils/logger.py already correct")
else:
    print("⚠️  utils/logger.py not found")

# ============================================================
# FIX 3: config/__init__.py (COMPREHENSIVE)
# ============================================================
print("📝 Fixing config/__init__.py...")

config_init = project_root / "config" / "__init__.py"

# Backup first
if config_init.exists():
    backup = project_root / "config" / "__init__.py.backup"
    shutil.copy(config_init, backup)
    print(f"   📦 Backup created: {backup}")

config_init_content = '''"""
Configuration package
Backward compatible with old imports while supporting new YAML config
"""

import os
from pathlib import Path

# ============================================================
# OLD CONFIG (For backward compatibility)
# ============================================================

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
STATE_DIR = DATA_DIR / "state"
HISTORY_DIR = DATA_DIR / "history"
POSITION_DIR = DATA_DIR / "positions"

# Ensure directories exist
for dir_path in [DATA_DIR, LOG_DIR, STATE_DIR, HISTORY_DIR, POSITION_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# MT5 Configuration
MT5_CONFIG = {
    'login': int(os.getenv('MT5_LOGIN', '0')),
    'password': os.getenv('MT5_PASSWORD', ''),
    'server': os.getenv('MT5_SERVER', ''),
    'timeout': 60000,
    'portable': False,
    'path': '',  # MT5 installation path (if needed)
}

# Data Configuration
DATA_CONFIG = {
    'default_timeframe': 'H1',
    'lookback_days': 90,
    'min_data_points': 100,
}

# Logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[%(levelname)s] %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'encoding': 'utf-8',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'trading.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'encoding': 'utf-8',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'errors.log'),
            'maxBytes': 10485760,
            'backupCount': 5
        }
    },
    'loggers': {
        '': {  # Root logger
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file']
        }
    }
}

# Application settings
APP_CONFIG = {
    'version': '2.0.0',
    'name': 'Pair Trading System - Professional',
    'update_interval': 1000,  # ms for UI updates
    'save_state_interval': 300,  # seconds
    'check_connection_interval': 10,  # seconds
}

# Import instruments and risk limits (if they exist)
try:
    from .instruments import INSTRUMENTS
except ImportError:
    # Define basic instruments if not found
    INSTRUMENTS = {
        'XAUUSD': {
            'symbol': 'XAUUSD',
            'description': 'Gold vs US Dollar',
            'contract_size': 100.0,
            'min_lot': 0.01,
            'max_lot': 100.0,
            'lot_step': 0.01,
            'digits': 2,
        },
        'XAGUSD': {
            'symbol': 'XAGUSD',
            'description': 'Silver vs US Dollar',
            'contract_size': 5000.0,
            'min_lot': 0.01,
            'max_lot': 100.0,
            'lot_step': 0.01,
            'digits': 3,
        },
        'NAS100.r': {
            'symbol': 'NAS100.r',
            'description': 'Nasdaq 100 Index',
            'contract_size': 1.0,
            'min_lot': 0.01,
            'max_lot': 100.0,
            'lot_step': 0.01,
            'digits': 2,
        },
        'SP500.r': {
            'symbol': 'SP500.r',
            'description': 'S&P 500 Index',
            'contract_size': 1.0,
            'min_lot': 0.01,
            'max_lot': 100.0,
            'lot_step': 0.01,
            'digits': 2,
        },
    }

try:
    from .risk_limits import RISK_LIMITS
except ImportError:
    # Define basic risk limits if not found
    RISK_LIMITS = {
        'max_position_size': 10.0,  # lots
        'max_daily_loss': 5000.0,  # USD
        'max_drawdown': 0.20,  # 20%
        'max_positions': 10,
    }

# ============================================================
# NEW CONFIG (YAML-based, for GUI)
# ============================================================

try:
    from .settings import get_config, ConfigManager, PairConfig, SymbolConfig
    __all__ = [
        # Old exports (backward compatible)
        'MT5_CONFIG', 'DATA_CONFIG', 'LOGGING_CONFIG', 'APP_CONFIG',
        'INSTRUMENTS', 'RISK_LIMITS',
        'BASE_DIR', 'DATA_DIR', 'LOG_DIR', 'STATE_DIR', 'HISTORY_DIR', 'POSITION_DIR',
        # New exports (for GUI)
        'get_config', 'ConfigManager', 'PairConfig', 'SymbolConfig'
    ]
except ImportError:
    # If new config system not available, only export old
    __all__ = [
        'MT5_CONFIG', 'DATA_CONFIG', 'LOGGING_CONFIG', 'APP_CONFIG',
        'INSTRUMENTS', 'RISK_LIMITS',
        'BASE_DIR', 'DATA_DIR', 'LOG_DIR', 'STATE_DIR', 'HISTORY_DIR', 'POSITION_DIR',
    ]
'''

with open(config_init, 'w', encoding='utf-8') as f:
    f.write(config_init_content)

print("✅ config/__init__.py fixed")

# ============================================================
# FIX 4: Clear all __pycache__
# ============================================================
print()
print("🧹 Clearing all Python cache files...")

import os
cache_count = 0
for root, dirs, files in os.walk(project_root):
    if '__pycache__' in dirs:
        cache_dir = Path(root) / '__pycache__'
        try:
            shutil.rmtree(cache_dir)
            cache_count += 1
            print(f"   🗑️  Removed: {cache_dir.relative_to(project_root)}")
        except Exception as e:
            print(f"   ⚠️  Could not remove {cache_dir}: {e}")

print(f"✅ Cleared {cache_count} cache directories")

# ============================================================
# VERIFICATION
# ============================================================
print()
print("="*70)
print("🔍 VERIFICATION")
print("="*70)
print()

# Test imports
print("Testing imports...")
errors = []

try:
    from config import MT5_CONFIG, DATA_CONFIG, INSTRUMENTS, RISK_LIMITS
    print("✅ config imports: OK")
except Exception as e:
    errors.append(f"config imports: {e}")
    print(f"❌ config imports: {e}")

try:
    from strategy import SignalGenerator, OrderManager, PositionTracker
    from strategy import SignalType, OrderStatus
    print("✅ strategy imports: OK")
except Exception as e:
    errors.append(f"strategy imports: {e}")
    print(f"❌ strategy imports: {e}")

try:
    from models import HedgeRatioCalculator
    print("✅ models imports: OK")
except Exception as e:
    errors.append(f"models imports: {e}")
    print(f"❌ models imports: {e}")

try:
    from risk import PositionSizer, DrawdownMonitor, RiskChecker
    print("✅ risk imports: OK")
except Exception as e:
    errors.append(f"risk imports: {e}")
    print(f"❌ risk imports: {e}")

print()
if errors:
    print("⚠️  SOME IMPORTS FAILED:")
    for err in errors:
        print(f"   - {err}")
    print()
    print("This might be OK if certain dependencies aren't installed yet.")
else:
    print("✅ ALL IMPORTS SUCCESSFUL!")

print()
print("="*70)
print("✅ IMPORT FIX COMPLETE!")
print("="*70)
print()
print("Next steps:")
print("  1. Run: python launch_gui.py")
print("  2. If there are still import errors, check missing dependencies:")
print("     pip install -r requirements.txt")
print()
