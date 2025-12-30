"""
Setup Recovery - Handle position recovery on startup

Workflow:
1. Load saved setups from disk
2. Verify positions still exist on MT5
3. If mismatch → Ask user to close all
4. If user confirms → Close all positions in setup
"""

import logging
import MetaTrader5 as mt5
from typing import List, Tuple
from core.setup_tracker import SetupTracker, Setup

logger = logging.getLogger(__name__)


class SetupRecovery:
    """
    Handle setup recovery on startup
    
    Recovery workflow:
    1. Load setups from disk
    2. Check MT5 for each setup
    3. If positions missing → user confirmation to close all
    """
    
    def __init__(self, setup_tracker: SetupTracker):
        self.setup_tracker = setup_tracker
    
    def check_all_setups(self) -> Tuple[List[Setup], List[Setup]]:
        """
        Check all active setups
        
        Returns:
            (valid_setups, invalid_setups)
        """
        valid = []
        invalid = []
        
        active_setups = self.setup_tracker.get_active_setups()
        
        if not active_setups:
            logger.info("No active setups to recover")
            return [], []
        
        logger.info(f"Checking {len(active_setups)} active setups...")
        
        for setup in active_setups:
            all_found, missing = self.setup_tracker.verify_setup_on_mt5(
                setup.setup_id, None
            )
            
            if all_found:
                valid.append(setup)
                logger.info(f"✓ Setup {setup.setup_id}: OK ({len(setup.positions)} positions)")
            else:
                invalid.append(setup)
                logger.warning(f"✗ Setup {setup.setup_id}: INVALID ({len(missing)} missing)")
        
        return valid, invalid
    
    def close_all_positions_in_setup(self, setup_id: str) -> bool:
        """
        Close ALL positions in a setup (no comment verification)
        
        Args:
            setup_id: Setup to close
            
        Returns:
            True if all closed successfully
        """
        tickets = self.setup_tracker.get_all_setup_tickets(setup_id)
        
        if not tickets:
            logger.warning(f"No tickets found for setup {setup_id}")
            return False
        
        logger.info(f"Closing {len(tickets)} positions in setup {setup_id}...")
        
        success_count = 0
        failed_tickets = []
        
        for ticket in tickets:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.warning(f"  Position {ticket} not found (already closed?)")
                continue
            
            position = position[0]
            
            # Determine close type
            if position.type == mt5.ORDER_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
            else:
                close_type = mt5.ORDER_TYPE_BUY
            
            # Close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_type,
                "position": ticket,
                "magic": position.magic,
                "comment": f"CLOSE_SETUP_{setup_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"  ✗ Failed to close {ticket}: order_send returned None")
                failed_tickets.append(ticket)
                continue
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"  ✗ Failed to close {ticket}: {result.comment}")
                failed_tickets.append(ticket)
            else:
                logger.info(f"  ✓ Closed {ticket}: {position.symbol} {position.volume} lots")
                success_count += 1
        
        # Mark setup as closed
        if success_count == len(tickets):
            self.setup_tracker.close_setup(setup_id, exit_zscore=0.0)
            logger.info(f"✓ All {len(tickets)} positions closed successfully")
            return True
        else:
            logger.warning(f"⚠ Partial close: {success_count}/{len(tickets)} closed")
            logger.warning(f"  Failed tickets: {failed_tickets}")
            return False
    
    def prompt_user_close_all(self, setup: Setup) -> bool:
        """
        Ask user if they want to close all positions in setup
        
        Args:
            setup: The invalid setup
            
        Returns:
            True if user wants to close all
        """
        print("\n" + "="*70)
        print("⚠️  SETUP MISMATCH DETECTED")
        print("="*70)
        print(f"Setup ID: {setup.setup_id}")
        print(f"Entry: {setup.entry_time}")
        print(f"Side: {setup.side} | Pair: {setup.pair}")
        print(f"Entry Z-score: {setup.entry_zscore:.2f}")
        print(f"Total positions in setup: {len(setup.positions)}")
        print("\nSome positions are missing on MT5!")
        print("This could mean:")
        print("  1. Positions were manually closed")
        print("  2. MT5 restarted and positions lost")
        print("  3. File out of sync")
        print("\n" + "="*70)
        
        # Show positions
        print("\nSetup positions:")
        for i, pos in enumerate(setup.positions, 1):
            print(f"  {i}. {pos.spread_id} - Primary: {pos.mt5_primary_ticket}, "
                  f"Secondary: {pos.mt5_secondary_ticket}")
        
        print("\n" + "="*70)
        print("OPTIONS:")
        print("  1. Close ALL positions in this setup")
        print("  2. Keep setup and continue (risky - positions may be incomplete)")
        print("  3. Exit and investigate manually")
        print("="*70)
        
        while True:
            choice = input("\nYour choice (1/2/3): ").strip()
            
            if choice == '1':
                return True
            elif choice == '2':
                logger.warning("User chose to keep invalid setup - continuing at own risk")
                return False
            elif choice == '3':
                print("\nExiting for manual investigation...")
                import sys
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def recover_or_close_all(self) -> List[Setup]:
        """
        Main recovery workflow
        
        Returns:
            List of valid setups to continue with
        """
        logger.info("="*70)
        logger.info("SETUP RECOVERY - Checking saved setups...")
        logger.info("="*70)
        
        valid_setups, invalid_setups = self.check_all_setups()
        
        if not invalid_setups:
            logger.info("✓ All setups valid - continuing")
            return valid_setups
        
        # Handle each invalid setup
        logger.warning(f"\n⚠ Found {len(invalid_setups)} invalid setup(s)")
        
        for setup in invalid_setups:
            # Ask user what to do
            if self.prompt_user_close_all(setup):
                logger.info(f"\nClosing all positions in setup {setup.setup_id}...")
                success = self.close_all_positions_in_setup(setup.setup_id)
                
                if success:
                    logger.info("✓ Setup closed successfully")
                else:
                    logger.error("✗ Failed to close some positions")
                    logger.error("  Please close manually in MT5")
            else:
                # User chose to keep invalid setup
                valid_setups.append(setup)
        
        logger.info("="*70)
        logger.info(f"RECOVERY COMPLETE - {len(valid_setups)} active setups")
        logger.info("="*70)
        
        return valid_setups
