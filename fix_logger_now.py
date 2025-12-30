"""
IMMEDIATE FIX for logger import error
Run this right now in F:\pair_trading_pro
"""

from pathlib import Path

print("="*70)
print("FIXING LOGGER IMPORT ERROR")
print("="*70)
print()

# Fix utils/logger.py
logger_file = Path("utils/logger.py")

if logger_file.exists():
    print("📝 Fixing utils/logger.py...")
    
    content = logger_file.read_text(encoding='utf-8')
    
    if "from config.settings import LOGGING_CONFIG" in content:
        # Fix the import
        content = content.replace(
            "from config.settings import LOGGING_CONFIG",
            "from config import LOGGING_CONFIG"
        )
        
        # Write back
        logger_file.write_text(content, encoding='utf-8')
        
        print("✅ Fixed! Changed:")
        print("   FROM: from config.settings import LOGGING_CONFIG")
        print("   TO:   from config import LOGGING_CONFIG")
    else:
        print("✅ Already correct!")
else:
    print("❌ utils/logger.py not found!")
    print("   Make sure you're in F:\\pair_trading_pro")

print()
print("="*70)
print("Now try: python launch_gui.py")
print("="*70)
