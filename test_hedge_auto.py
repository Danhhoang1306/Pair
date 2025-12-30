"""
Automatic Hedge Adjustment Test - No User Input
Tests single-leg order placement automatically
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from core.mt5_trade_executor import MT5TradeExecutor

def test_single_leg_auto():
    """
    Automatic test - places 0.01 lots BUY ETHUSD
    This should make position count ODD if working correctly
    """
    
    print("="*70)
    print("AUTO HEDGE ADJUSTMENT TEST - Single Leg Order")
    print("="*70)
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return False
    
    print(f"✅ MT5 connected")
    print(f"   Account: {mt5.account_info().login}")
    print(f"   Balance: ${mt5.account_info().balance:,.2f}")
    print()
    
    # Get current positions
    positions = mt5.positions_get()
    initial_count = len(positions)
    print(f"📊 BEFORE: {initial_count} positions")
    
    # Count BTC and ETH
    btc_count = len([p for p in positions if 'BTC' in p.symbol])
    eth_count = len([p for p in positions if 'ETH' in p.symbol])
    print(f"   BTC: {btc_count}, ETH: {eth_count}")
    
    # Calculate imbalance
    btc_lots = sum(p.volume if p.type == 0 else -p.volume 
                   for p in positions if 'BTC' in p.symbol)
    eth_lots = sum(p.volume if p.type == 0 else -p.volume 
                   for p in positions if 'ETH' in p.symbol)
    
    print(f"   BTC net: {btc_lots:+.4f} lots")
    print(f"   ETH net: {eth_lots:+.4f} lots")
    print()
    
    # Test parameters
    symbol = 'ETHUSD'
    order_type = 'BUY'
    volume = 0.01
    
    print("="*70)
    print(f"TEST: {order_type} {volume} lots {symbol}")
    print("="*70)
    print()
    
    # Initialize executor
    executor = MT5TradeExecutor(
        magic_number=234000,
        volume_multiplier=1.0,
        primary_symbol='BTCUSD',
        secondary_symbol='ETHUSD'
    )
    
    # Place order
    result = executor.place_market_order(
        symbol=symbol,
        order_type=order_type,
        volume=volume,
        comment="AUTO_TEST:HEDGE"
    )
    
    print()
    success = False
    
    if result.success:
        print("✅ ORDER EXECUTED!")
        print(f"   Ticket: {result.order_ticket}")
        print(f"   Volume: {result.volume} lots")
        print(f"   Price: ${result.price:.2f}")
        print()
        
        # Check new position count
        import time
        time.sleep(1)  # Wait for MT5 to update
        
        new_positions = mt5.positions_get()
        new_count = len(new_positions)
        
        print(f"📊 AFTER: {new_count} positions")
        print(f"   Change: {new_count - initial_count:+d} positions")
        print()
        
        # Verify
        if new_count == initial_count + 1:
            print("=" * 70)
            print("✅ SUCCESS: Added exactly 1 position!")
            print("=" * 70)
            
            if new_count % 2 == 1:
                print("✅ Position count is ODD - Single leg works!")
            else:
                print("✅ Position count is EVEN (but added only 1)")
            
            success = True
            
        elif new_count == initial_count + 2:
            print("=" * 70)
            print("❌ FAILURE: Added 2 positions!")
            print("=" * 70)
            print("❌ place_market_order opened a SPREAD, not single leg!")
            success = False
            
        else:
            print("=" * 70)
            print(f"⚠️  UNEXPECTED: Position count changed by {new_count - initial_count}")
            print("=" * 70)
            success = False
        
    else:
        print("❌ ORDER FAILED!")
        print(f"   Error: {result.comment}")
        success = False
    
    print()
    print("="*70)
    
    mt5.shutdown()
    return success

if __name__ == "__main__":
    success = test_single_leg_auto()
    sys.exit(0 if success else 1)
