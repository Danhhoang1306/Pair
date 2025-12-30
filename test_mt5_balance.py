"""
Quick MT5 Balance Test
Run this to check if MT5RiskMonitor can get balance
"""

import sys
sys.path.insert(0, '.')

print("="*70)
print("MT5 BALANCE TEST")
print("="*70)

try:
    # Test 1: Import
    print("\n1. Importing MT5RiskMonitor...")
    from risk.mt5_risk_monitor import MT5RiskMonitor
    print("   ✅ Import successful")
    
    # Test 2: Create monitor
    print("\n2. Creating monitor...")
    monitor = MT5RiskMonitor()
    print("   ✅ Monitor created")
    
    # Test 3: Get metrics
    print("\n3. Getting MT5 metrics...")
    metrics = monitor.get_metrics(
        primary_symbol='XAUUSD',
        secondary_symbol='XAGUSD',
        target_hedge_ratio=0.7179,
        max_risk_pct=0.02
    )
    
    if metrics:
        print("   ✅ Metrics retrieved!")
        print("\n" + "="*70)
        print("RESULTS:")
        print("="*70)
        print(f"Balance:    ${metrics.balance:,.2f}")
        print(f"Equity:     ${metrics.equity:,.2f}")
        print(f"Profit:     ${metrics.profit:,.2f}")
        print(f"Margin:     ${metrics.margin:,.2f}")
        print(f"Free:       ${metrics.margin_free:,.2f}")
        print(f"Level:      {metrics.margin_level:.1f}%")
        print(f"Positions:  {metrics.total_positions}")
        print(f"Primary:    {metrics.primary_lots:+.4f} lots")
        print(f"Secondary:  {metrics.secondary_lots:+.4f} lots")
        print(f"Imbalance:  {metrics.hedge_imbalance:+.4f} lots ({metrics.hedge_imbalance_pct:+.2%})")
        print(f"Stop Loss:  ${metrics.stop_loss_level:,.2f}")
        print(f"Risk Amt:   ${metrics.risk_amount:,.2f}")
        print("="*70)
        
        # Check if balance is 0
        if metrics.balance == 0:
            print("\n⚠️  WARNING: Balance is $0.00!")
            print("   This might be why GUI shows blank")
            print("   Check your MT5 account balance")
        else:
            print(f"\n✅ Balance is ${metrics.balance:,.2f}")
            print("   If GUI still blank, it's a display issue")
            
    else:
        print("   ❌ Metrics is None!")
        print("\n⚠️  MT5RiskMonitor.get_metrics() returned None")
        print("   Possible causes:")
        print("   - MT5 not connected")
        print("   - Account info failed")
        print("   - Check MT5 terminal")
        
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    print("\n   Make sure you're in the project directory!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
