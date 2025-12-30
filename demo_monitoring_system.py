"""
COMPLETE SYSTEM FLOW DEMONSTRATION
====================================

This demonstrates the complete position monitoring and recovery system:
1. Setup flag management
2. Position monitoring during runtime
3. Recovery on system restart
4. User confirmation flow
"""

import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_setup_flag_manager():
    """Demo: Setup flag manager"""
    print("\n" + "="*80)
    print("DEMO 1: SETUP FLAG MANAGER")
    print("="*80)
    
    from core.setup_flag_manager import SetupFlagManager
    
    flag_manager = SetupFlagManager(data_dir='demo_positions')
    
    # Scenario 1: Check flag (should be False initially)
    print("\n1. Initial check:")
    is_active = flag_manager.is_setup_active()
    print(f"   Setup active? {is_active}")
    
    # Scenario 2: Mark setup active
    print("\n2. Opening first position...")
    flag_manager.mark_setup_active(
        spread_id='spread_123',
        metadata={
            'side': 'LONG',
            'entry_zscore': 2.5,
            'hedge_ratio': 85.5
        }
    )
    print(f"   Setup active? {flag_manager.is_setup_active()}")
    
    # Scenario 3: Get setup info
    print("\n3. Get setup info:")
    info = flag_manager.get_setup_info()
    if info:
        print(f"   Spread ID: {info['spread_id']}")
        print(f"   Activated at: {info['activated_at']}")
        print(f"   Metadata: {info['metadata']}")
    
    # Scenario 4: Mark setup inactive
    print("\n4. Closing all positions...")
    flag_manager.mark_setup_inactive("All positions closed")
    print(f"   Setup active? {flag_manager.is_setup_active()}")
    
    print("\n✅ Setup flag manager demo complete\n")


def demo_position_monitor():
    """Demo: Position monitor"""
    print("\n" + "="*80)
    print("DEMO 2: POSITION MONITOR")
    print("="*80)
    
    from core.position_monitor import PositionMonitor
    import time
    
    # Create monitor
    monitor = PositionMonitor(
        check_interval=2,  # Check every 2 seconds (faster for demo)
        user_response_timeout=10  # 10 second timeout for demo
    )
    
    # Setup callbacks
    def on_missing(tickets):
        print(f"\n🚨 CALLBACK: Positions missing: {tickets}")
    
    def on_confirmed(tickets):
        print(f"\n✅ CALLBACK: User confirmed rebalance for: {tickets}")
    
    def on_timeout():
        print(f"\n❌ CALLBACK: User timeout - closing all")
    
    monitor.on_position_missing = on_missing
    monitor.on_user_confirmed = on_confirmed
    monitor.on_user_timeout = on_timeout
    
    # Scenario 1: Register positions
    print("\n1. Registering positions to monitor:")
    monitor.register_position(ticket=123456, symbol='XAUUSD')
    monitor.register_position(ticket=123457, symbol='XAGUSD')
    
    monitored = monitor.get_monitored_tickets()
    print(f"   Currently monitoring: {monitored}")
    
    # Scenario 2: Start monitoring
    print("\n2. Starting monitor thread...")
    monitor.start()
    print("   Monitor is now running in background")
    
    # Scenario 3: Simulate normal operation
    print("\n3. Simulating normal operation (5 seconds)...")
    time.sleep(5)
    print("   All positions OK")
    
    # Scenario 4: Unregister one position (simulating normal close)
    print("\n4. Closing position 123456 normally...")
    monitor.unregister_position(123456)
    monitored = monitor.get_monitored_tickets()
    print(f"   Still monitoring: {monitored}")
    
    # Scenario 5: Clear all
    print("\n5. Closing all positions...")
    monitor.clear_all()
    monitored = monitor.get_monitored_tickets()
    print(f"   Monitoring: {monitored} (should be empty)")
    
    # Stop monitor
    print("\n6. Stopping monitor...")
    monitor.stop()
    
    print("\n✅ Position monitor demo complete\n")


def demo_startup_recovery_flow():
    """Demo: Complete startup recovery flow"""
    print("\n" + "="*80)
    print("DEMO 3: STARTUP RECOVERY FLOW")
    print("="*80)
    
    from core.setup_flag_manager import SetupFlagManager
    from core.position_persistence import PositionPersistence, PersistedPosition
    from datetime import datetime
    
    data_dir = 'demo_positions'
    flag_manager = SetupFlagManager(data_dir=data_dir)
    persistence = PositionPersistence(data_dir=data_dir)
    
    # SCENARIO A: No flag set (clean start)
    print("\n" + "-"*80)
    print("SCENARIO A: Clean Start")
    print("-"*80)
    
    flag_manager.mark_setup_inactive("Reset for demo")
    
    print("\n1. System startup...")
    if flag_manager.is_setup_active():
        print("   ⚠️  Active setup detected - checking positions...")
    else:
        print("   ✅ No active setup - starting fresh")
    
    # SCENARIO B: Flag set + positions exist (normal recovery)
    print("\n" + "-"*80)
    print("SCENARIO B: Normal Recovery (all positions exist)")
    print("-"*80)
    
    # Setup: Create flag and positions
    print("\n1. Simulating previous session...")
    flag_manager.mark_setup_active(
        spread_id='spread_abc',
        metadata={'side': 'LONG', 'entry_zscore': 2.5}
    )
    
    # Create fake positions
    gold_pos = PersistedPosition(
        position_id='pos_gold_1',
        spread_id='spread_abc',
        mt5_ticket=999001,
        symbol='XAUUSD',
        side='LONG',
        volume=0.1,
        entry_price=2650.50,
        entry_time=datetime.now().isoformat(),
        entry_zscore=2.5,
        hedge_ratio=85.5,
        is_gold=True,
        created_at=datetime.now().isoformat(),
        last_updated=datetime.now().isoformat()
    )
    
    silver_pos = PersistedPosition(
        position_id='pos_silver_1',
        spread_id='spread_abc',
        mt5_ticket=999002,
        symbol='XAGUSD',
        side='SHORT',
        volume=8.55,
        entry_price=31.20,
        entry_time=datetime.now().isoformat(),
        entry_zscore=2.5,
        hedge_ratio=85.5,
        is_gold=False,
        created_at=datetime.now().isoformat(),
        last_updated=datetime.now().isoformat()
    )
    
    persistence.save_position(gold_pos)
    persistence.save_position(silver_pos)
    
    print("   Saved 2 positions to disk")
    
    # Recovery flow
    print("\n2. System restart...")
    print("   Checking flag...")
    if flag_manager.is_setup_active():
        print("   ⚠️  Active setup detected!")
        
        print("\n3. Loading positions from disk...")
        persisted = persistence.load_active_positions()
        print(f"   Found {len(persisted)} positions")
        
        for pos_id, pos in persisted.items():
            print(f"   • {pos.symbol} {pos.side} {pos.volume} lots @ {pos.entry_price:.2f}")
        
        print("\n4. Checking if positions exist on MT5...")
        print("   ⚠️  NOTE: In real system, would query MT5 here")
        print("   ✅ SIMULATED: All positions found on MT5")
        
        print("\n5. User confirmation...")
        print("   ⏰ Waiting 60 seconds for user response...")
        print("   Options:")
        print("     1. CONTINUE - Resume trading")
        print("     2. CLOSE ALL - Close and start fresh")
        print("   ✅ SIMULATED: User chose CONTINUE")
        
        print("\n6. Restoring positions to tracker...")
        print("   ✅ Positions restored")
        print("   ✅ Monitor started")
    
    # SCENARIO C: Flag set + positions missing (incomplete recovery)
    print("\n" + "-"*80)
    print("SCENARIO C: Incomplete Recovery (positions closed manually)")
    print("-"*80)
    
    print("\n1. System restart...")
    if flag_manager.is_setup_active():
        print("   ⚠️  Active setup detected!")
        
        print("\n2. Loading positions from disk...")
        persisted = persistence.load_active_positions()
        print(f"   Found {len(persisted)} positions")
        
        print("\n3. Checking if positions exist on MT5...")
        print("   ⚠️  NOTE: In real system, would query MT5 here")
        print("   ❌ SIMULATED: Position 999001 NOT FOUND (manually closed)")
        print("   ✅ SIMULATED: Position 999002 still exists")
        
        print("\n4. Incomplete spread detected!")
        print("   Options:")
        print("     1. REBALANCE - Reopen missing positions")
        print("     2. CLOSE ALL - Close remaining positions")
        print("   ⚠️  SIMULATED: User timeout → AUTO CLOSE ALL")
        
        print("\n5. Closing all positions...")
        print("   ✅ All positions closed")
        print("   ✅ Flag cleared")
    
    # Cleanup
    persistence.clear_all_positions()
    flag_manager.clear_flag()
    
    print("\n✅ Startup recovery flow demo complete\n")


def demo_runtime_monitoring():
    """Demo: Runtime monitoring detecting manual closes"""
    print("\n" + "="*80)
    print("DEMO 4: RUNTIME MONITORING")
    print("="*80)
    
    print("\n1. System is running normally...")
    print("   Positions open: 2 (XAUUSD, XAGUSD)")
    print("   Monitor checking every 5 seconds...")
    
    print("\n2. User manually closes position on MT5...")
    print("   ⚠️  MT5 Terminal: Position 123456 CLOSED")
    
    print("\n3. Monitor detects missing position!")
    print("   🚨 ALERT: Position 123456 (XAUUSD) missing!")
    print("   📋 Notification sent to user")
    
    print("\n4. Waiting for user response (60 seconds)...")
    print("   Options:")
    print("     1. REBALANCE - Reopen missing position")
    print("     2. CLOSE ALL - Close all positions")
    print("     3. NO RESPONSE - Auto close after timeout")
    
    print("\n5. SCENARIO A: User confirms REBALANCE")
    print("   ✅ User clicked 'REBALANCE'")
    print("   🔄 Reopening missing position...")
    print("   ✅ Position restored")
    
    print("\n6. SCENARIO B: User timeout")
    print("   ❌ No response after 60 seconds")
    print("   🚨 AUTO CLOSING ALL POSITIONS...")
    print("   ✅ All positions closed")
    print("   ✅ Flag cleared")
    
    print("\n✅ Runtime monitoring demo complete\n")


def demo_complete_lifecycle():
    """Demo: Complete lifecycle from entry to exit"""
    print("\n" + "="*80)
    print("DEMO 5: COMPLETE LIFECYCLE")
    print("="*80)
    
    print("\n📊 PHASE 1: ENTRY")
    print("-"*80)
    print("1. Signal detected: LONG SPREAD (z-score = 2.5)")
    print("2. Opening positions on MT5...")
    print("   ✅ XAUUSD LONG 0.1 lots @ 2650.50 (Ticket: 123456)")
    print("   ✅ XAGUSD SHORT 8.55 lots @ 31.20 (Ticket: 123457)")
    print("3. Saving to disk...")
    print("   ✅ Positions persisted")
    print("4. Setting flag...")
    print("   ✅ Setup flag: ACTIVE")
    print("5. Registering with monitor...")
    print("   ✅ Monitoring: [123456, 123457]")
    
    print("\n📈 PHASE 2: RUNTIME MONITORING")
    print("-"*80)
    print("1. Monitor checking every 5 seconds...")
    print("2. Positions status: OK")
    print("3. Z-score moving toward reversion...")
    
    print("\n🔄 PHASE 3: REBALANCE (if hedge drifts)")
    print("-"*80)
    print("1. Hedge ratio drifted > 5%")
    print("2. Rebalancing silver position...")
    print("   ✅ Adjusted XAGUSD volume")
    print("3. Monitor updated with new tickets")
    
    print("\n🛑 PHASE 4: EXIT")
    print("-"*80)
    print("1. Signal detected: CLOSE SPREAD (z-score = 0.1)")
    print("2. Closing positions on MT5...")
    print("   ✅ Closed ticket 123456")
    print("   ✅ Closed ticket 123457")
    print("3. Unregistering from monitor...")
    print("   ✅ Monitor: []")
    print("4. Archiving positions...")
    print("   ✅ Positions archived")
    print("5. Clearing flag...")
    print("   ✅ Setup flag: INACTIVE")
    print("6. P&L: $+150.50")
    
    print("\n🔄 PHASE 5: RESTART RECOVERY")
    print("-"*80)
    print("1. System restarted...")
    print("2. Checking flag...")
    print("   ✅ Flag: INACTIVE (no recovery needed)")
    print("3. Starting fresh...")
    
    print("\n✅ Complete lifecycle demo complete\n")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("POSITION MONITORING SYSTEM - COMPLETE DEMONSTRATION")
    print("="*80)
    
    try:
        demo_setup_flag_manager()
        demo_position_monitor()
        demo_startup_recovery_flow()
        demo_runtime_monitoring()
        demo_complete_lifecycle()
        
        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nKey Features Demonstrated:")
        print("  ✅ Setup flag management (ACTIVE/INACTIVE)")
        print("  ✅ Position monitoring (real-time)")
        print("  ✅ Startup recovery (with user confirmation)")
        print("  ✅ Runtime monitoring (detect manual closes)")
        print("  ✅ Complete lifecycle (entry → monitoring → exit)")
        print("\nNext Steps:")
        print("  1. Integrate with GUI for user confirmation dialogs")
        print("  2. Add rebalance logic implementation")
        print("  3. Test with real MT5 connection")
        print("  4. Add email/SMS notifications")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    import shutil
    if Path('demo_positions').exists():
        shutil.rmtree('demo_positions')
        print("Cleaned up demo files\n")


if __name__ == '__main__':
    main()
