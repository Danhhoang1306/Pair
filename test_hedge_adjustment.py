"""
Manual Hedge Adjustment Test
Tests single-leg order placement for hedge rebalancing
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from core.mt5_trade_executor import MT5TradeExecutor

def test_single_leg_order():
    """Test placing a single leg order for hedge adjustment"""
    
    print("="*70)
    print("HEDGE ADJUSTMENT TEST - Single Leg Order")
    print("="*70)
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return
    
    print(f"✅ MT5 connected")
    print(f"   Account: {mt5.account_info().login}")
    print(f"   Balance: ${mt5.account_info().balance:,.2f}")
    print()
    
    # Get current positions
    positions = mt5.positions_get()
    print(f"📊 Current positions: {len(positions)}")
    
    # Count BTC and ETH
    btc_count = len([p for p in positions if 'BTC' in p.symbol])
    eth_count = len([p for p in positions if 'ETH' in p.symbol])
    print(f"   BTC positions: {btc_count}")
    print(f"   ETH positions: {eth_count}")
    print(f"   Total: {btc_count + eth_count}")
    print()
    
    # Calculate imbalance
    btc_lots = sum(p.volume if p.type == 0 else -p.volume 
                   for p in positions if 'BTC' in p.symbol)
    eth_lots = sum(p.volume if p.type == 0 else -p.volume 
                   for p in positions if 'ETH' in p.symbol)
    
    print(f"📊 Current Positions:")
    print(f"   BTC: {btc_lots:+.4f} lots")
    print(f"   ETH: {eth_lots:+.4f} lots")
    print()
    
    # Ask user for test
    print("TEST OPTIONS:")
    print("  1. Place small BUY ETHUSD order (0.01 lots)")
    print("  2. Place small SELL ETHUSD order (0.01 lots)")
    print("  3. Place small BUY BTCUSD order (0.01 lots)")
    print("  4. Cancel")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '4':
        print("Cancelled")
        mt5.shutdown()
        return
    
    # Determine order params
    if choice == '1':
        symbol = 'ETHUSD'
        order_type = 'BUY'
        volume = 0.01
    elif choice == '2':
        symbol = 'ETHUSD'
        order_type = 'SELL'
        volume = 0.01
    elif choice == '3':
        symbol = 'BTCUSD'
        order_type = 'BUY'
        volume = 0.01
    else:
        print("Invalid choice")
        mt5.shutdown()
        return
    
    print()
    print("="*70)
    print(f"EXECUTING: {order_type} {volume} lots {symbol}")
    print("="*70)
    
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
        comment="HEDGE_TEST:MANUAL"
    )
    
    print()
    if result.success:
        print("✅ ORDER EXECUTED SUCCESSFULLY!")
        print(f"   Ticket: {result.order_ticket}")
        print(f"   Volume: {result.volume} lots")
        print(f"   Price: ${result.price:.2f}")
        print()
        
        # Check new position count
        new_positions = mt5.positions_get()
        print(f"📊 New position count: {len(new_positions)}")
        
        # Verify it's ODD
        if len(new_positions) % 2 == 1:
            print(f"   ✅ ODD number - Single leg worked!")
        else:
            print(f"   ❌ EVEN number - Something wrong!")
        
    else:
        print("❌ ORDER FAILED!")
        print(f"   Error: {result.comment}")
    
    print()
    print("="*70)
    
    mt5.shutdown()

if __name__ == "__main__":
    test_single_leg_order()
