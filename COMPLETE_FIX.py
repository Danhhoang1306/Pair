#!/usr/bin/env python3
"""
COMPLETE FIX - Replace ALL gold/silver references
Run this in F:\pair_trading_pro directory
"""

import os
import re
from pathlib import Path

def replace_in_file(filepath, replacements):
    """Apply replacements to a file"""
    print(f"Processing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"  ⚠️  File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = 0
        
        for old, new in replacements.items():
            if old in content:
                count = content.count(old)
                content = content.replace(old, new)
                changes += count
                print(f"  ✅ {old} → {new} ({count}x)")
        
        if content != original_content:
            # Backup
            with open(filepath + '.backup', 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Write new
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  💾 Saved {changes} changes")
            return True
        else:
            print(f"  ℹ️  No changes needed")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("=" * 80)
    print("COMPLETE GOLD/SILVER → PRIMARY/SECONDARY REPLACEMENT")
    print("=" * 80)
    print()
    
    # All replacements
    replacements = {
        # Variables
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
        'gold_vol': 'primary_vol',
        'silver_vol': 'secondary_vol',
        
        # Log messages
        'Gold:': 'Primary:',
        'Silver:': 'Secondary:',
        'Gold ': 'Primary ',
        'Silver ': 'Secondary ',
        '  Gold': '  Primary',
        '  Silver': '  Secondary',
    }
    
    # Files to process
    files = [
        'core/realtime_market_data.py',
        'core/data_manager.py',
        'core/mt5_connector.py',
        'main_cli.py',
        'strategy/signal_generator.py',  # ← CRITICAL!
    ]
    
    total_files = 0
    total_changes = 0
    
    for filepath in files:
        if replace_in_file(filepath, replacements):
            total_files += 1
    
    print()
    print("=" * 80)
    print(f"✅ COMPLETE! Processed {len(files)} files")
    print("=" * 80)
    print()
    print("🔍 Verify changes:")
    print("  1. Check .backup files for original versions")
    print("  2. Test: python launch_gui.py")
    print()

if __name__ == "__main__":
    main()
