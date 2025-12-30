"""
Position Monitoring System
Continuously monitors MT5 positions and detects manual closures
"""
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Set, Optional, Callable
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class PositionMonitor:
    """
    Monitors MT5 positions in real-time
    Detects manual closures and triggers recovery/rebalance
    """
    
    def __init__(self, check_interval: int = 5, user_response_timeout: int = 60):
        """
        Initialize position monitor
        
        Args:
            check_interval: How often to check MT5 positions (seconds)
            user_response_timeout: How long to wait for user response (seconds)
        """
        self.check_interval = check_interval
        self.user_response_timeout = user_response_timeout
        
        # Track expected positions (ticket -> symbol mapping)
        self.expected_tickets: Dict[int, str] = {}
        self.lock = threading.RLock()
        
        # Callbacks
        self.on_position_missing: Optional[Callable] = None
        self.on_user_confirmed: Optional[Callable] = None
        self.on_user_timeout: Optional[Callable] = None
        
        # User response tracking
        self.pending_user_response = False
        self.user_response_event = threading.Event()
        self.user_response = None
        
        # Running flag
        self.running = False
        self.monitor_thread = None
        
    def register_position(self, ticket: int, symbol: str):
        """Register a position to monitor"""
        with self.lock:
            self.expected_tickets[ticket] = symbol
            logger.info(f"🔍 Monitoring: Ticket {ticket} ({symbol})")
    
    def unregister_position(self, ticket: int):
        """Stop monitoring a position"""
        with self.lock:
            if ticket in self.expected_tickets:
                symbol = self.expected_tickets.pop(ticket)
                logger.info(f"🔍 Stopped monitoring: Ticket {ticket} ({symbol})")
    
    def clear_all(self):
        """Clear all monitored positions"""
        with self.lock:
            self.expected_tickets.clear()
            logger.info("🔍 Cleared all monitored positions")
    
    def get_monitored_tickets(self) -> Set[int]:
        """Get set of currently monitored tickets"""
        with self.lock:
            return set(self.expected_tickets.keys())
    
    def start(self):
        """Start monitoring thread"""
        if self.running:
            logger.warning("Position monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="PositionMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"🔍 Position monitor started (check interval: {self.check_interval}s)")
    
    def stop(self):
        """Stop monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🔍 Position monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_positions()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                import traceback
                traceback.print_exc()
    
    def _check_positions(self):
        """Check if all expected positions still exist on MT5"""
        with self.lock:
            if not self.expected_tickets:
                return
            
            # Get current MT5 positions
            mt5_positions = mt5.positions_get()
            if mt5_positions is None:
                logger.warning("Failed to get MT5 positions")
                return
            
            current_tickets = {pos.ticket for pos in mt5_positions}
            expected = set(self.expected_tickets.keys())
            
            # Find missing positions
            missing_tickets = expected - current_tickets
            
            if missing_tickets:
                # Positions were closed manually!
                logger.error("="*80)
                logger.error("⚠️  MANUAL CLOSURE DETECTED!")
                logger.error("="*80)
                
                for ticket in missing_tickets:
                    symbol = self.expected_tickets.get(ticket, "UNKNOWN")
                    logger.error(f"❌ Position MISSING: Ticket {ticket} ({symbol})")
                
                # Trigger callback
                if self.on_position_missing:
                    self.on_position_missing(missing_tickets)
                
                # Request user confirmation
                self._request_user_confirmation(missing_tickets)
    
    def _request_user_confirmation(self, missing_tickets: Set[int]):
        """
        Request user confirmation for rebalancing
        Wait up to user_response_timeout seconds
        """
        if self.pending_user_response:
            logger.warning("User response already pending")
            return
        
        self.pending_user_response = True
        self.user_response_event.clear()
        
        logger.warning("="*80)
        logger.warning("⚠️  POSITION(S) MANUALLY CLOSED - ACTION REQUIRED")
        logger.warning("="*80)
        logger.warning(f"Missing tickets: {missing_tickets}")
        logger.warning("")
        logger.warning("Options:")
        logger.warning("  1. REBALANCE - Reopen missing positions to restore hedge")
        logger.warning("  2. CLOSE ALL - Close all remaining positions")
        logger.warning("")
        logger.warning(f"⏰ Waiting {self.user_response_timeout}s for response...")
        logger.warning(f"⏰ If no response → AUTO CLOSE ALL positions")
        logger.warning("="*80)
        
        # Wait for user response with timeout
        response_received = self.user_response_event.wait(timeout=self.user_response_timeout)
        
        self.pending_user_response = False
        
        if not response_received:
            # Timeout - auto close all
            logger.error("❌ NO USER RESPONSE - AUTO CLOSING ALL POSITIONS")
            if self.on_user_timeout:
                self.on_user_timeout()
        else:
            # User responded
            if self.user_response == 'rebalance':
                logger.info("✅ User confirmed: REBALANCE")
                if self.on_user_confirmed:
                    self.on_user_confirmed(missing_tickets)
            else:
                logger.info("🚫 User declined: CLOSE ALL")
                if self.on_user_timeout:  # Same action as timeout
                    self.on_user_timeout()
    
    def confirm_rebalance(self):
        """User confirmed to rebalance"""
        self.user_response = 'rebalance'
        self.user_response_event.set()
    
    def confirm_close_all(self):
        """User confirmed to close all"""
        self.user_response = 'close_all'
        self.user_response_event.set()
