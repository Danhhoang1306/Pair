#!/usr/bin/env python3
"""
Replace all hardcoded gold/silver references with primary/secondary
Makes system generic for any pair
"""

import re
import os
from pathlib import Path

# Mapping of replacements
REPLACEMENTS = {
    # Variable names
    'gold_bid': 'primary_bid',
    'gold_ask': 'primary_ask',
    'silver_bid': 'secondary_bid',
    'silver_ask': 'secondary_ask',
    'gold_price': 'primary_price',
    'silver_price': 'secondary_price',
    'gold_df': 'primary_df',
    'silver_df': 'secondary_df',
    'gold_clean': 'primary_clean',
    'silver_clean': 'secondary_clean',
    'gold_lot_value': 'primary_lot_value',
    'silver_lot_value': 'secondary_lot_value',
    'current_gold_vol': 'current_primary_vol',
    'current_silver_vol': 'current_secondary_vol',
    'gold_tick': 'primary_tick',
    'silver_tick': 'secondary_tick',
    'gold_missing': 'primary_missing',
    'silver_missing': 'secondary_missing',
    'gold_bars': 'primary_bars',
    'silver_bars': 'secondary_bars',
    'gold_commission': 'primary_commission',
    'silver_commission': 'secondary_commission',
    'gold_vol': 'primary_vol',
    'silver_vol': 'secondary_vol',
    
    # In log messages (with context)
    'Gold:': 'Primary:',
    'Silver:': 'Secondary:',
    'Gold ': 'Primary ',
    'Silver ': 'Secondary ',
    '  Gold': '  Primary',
    '  Silver': '  Secondary',
    'Gold $': 'Primary $',
    'Silver $': 'Secondary $',
    'gold and silver': 'primary and secondary',
    '"Gold"': '"Primary"',
    '"Silver"': '"Secondary"',
    "'gold'": "'primary'",
    "'silver'": "'secondary'",
    '"gold"': '"primary"',
    '"silver"': '"secondary"',
    
    # Comments
    '# Gold': '# Primary',
    '# Silver': '# Secondary',
    '# gold': '# primary',
    '# silver': '# secondary',
    'for gold': 'for primary',
    'for silver': 'for secondary',
    'Gold /oz': 'Primary /oz',
    'Silver /oz': 'Secondary /oz',
}

# Files to process
FILES_TO_PROCESS = [
    'core/realtime_market_data.py',
    'core/data_manager.py',
    'core/mt5_connector.py',
    'main_cli.py',
]

def replace_in_file(filepath, replacements):
    """Replace all occurrences in a file"""
    print(f"\nProcessing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"  Skipped (not found)")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = 0
    
    # Apply replacements
    for old, new in replacements.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            changes += count
            print(f"  Replaced '{old}' → '{new}' ({count} times)")
    
    if content != original:
        # Backup
        backup = filepath + '.bak'
        with open(backup, 'w', encoding='utf-8') as f:
            f.write(original)
        
        # Write new
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Saved {changes} changes (backup: {backup})")
    else:
        print(f"  No changes needed")

def main():
    print("=" * 70)
    print("REPLACING GOLD/SILVER WITH PRIMARY/SECONDARY")
    print("=" * 70)
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    total_files = 0
    total_changes = 0
    
    for filepath in FILES_TO_PROCESS:
        replace_in_file(filepath, REPLACEMENTS)
        total_files += 1
    
    print("\n" + "=" * 70)
    print(f"✅ DONE! Processed {total_files} files")
    print("=" * 70)
    print("\n🔍 Review changes and test!")
    print("   Backups created with .bak extension")

if __name__ == "__main__":
    main()
