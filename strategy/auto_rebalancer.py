"""
Auto-Rebalance Module
Automatically rebalances hedge when MT5 lot rounding causes sufficient imbalance
"""

import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AutoRebalancer:
    """
    Monitors hedge imbalance and triggers rebalance when threshold is reached
    
    Rationale:
    - MT5 rounds lots to minimum step (e.g., 0.01)
    - Over time, rounding errors accumulate
    - When imbalance >= 0.01 lot (minimum tradeable), we can rebalance
    
    Example:
        >>> rebalancer = AutoRebalancer(min_imbalance_lots=0.01)
        >>> if rebalancer.should_rebalance(imbalance=0.012):
        ...     # Execute rebalance trade
    """
    
    def __init__(self,
                 min_imbalance_lots: float = 0.01,  # Minimum lots to trigger
                 min_imbalance_pct: float = 0.05,   # 5% imbalance
                 cooldown_seconds: int = 3600):      # 1 hour cooldown
        """
        Initialize auto-rebalancer
        
        Args:
            min_imbalance_lots: Minimum absolute lot imbalance to trigger (default 0.01)
            min_imbalance_pct: Minimum percentage imbalance (default 5%)
            cooldown_seconds: Minimum time between rebalances (default 1 hour)
        """
        self.min_imbalance_lots = min_imbalance_lots
        self.min_imbalance_pct = min_imbalance_pct
        self.cooldown_seconds = cooldown_seconds
        
        self.last_rebalance_time: Optional[datetime] = None
        self.rebalance_count = 0
        
        logger.info(f"AutoRebalancer initialized:")
        logger.info(f"  Min imbalance: {min_imbalance_lots:.4f} lots ({min_imbalance_pct:.1%})")
        logger.info(f"  Cooldown: {cooldown_seconds}s ({cooldown_seconds/3600:.1f}h)")
    
    def should_rebalance(self,
                        imbalance_lots: float,
                        imbalance_pct: float) -> bool:
        """
        Check if rebalance should be triggered
        
        Args:
            imbalance_lots: Absolute lot imbalance (e.g., 0.012)
            imbalance_pct: Percentage imbalance (e.g., 0.05 = 5%)
            
        Returns:
            True if rebalance should be executed
        """
        # Check cooldown
        if self.last_rebalance_time:
            time_since_last = (datetime.now() - self.last_rebalance_time).total_seconds()
            if time_since_last < self.cooldown_seconds:
                logger.debug(f"Rebalance on cooldown ({time_since_last:.0f}s / {self.cooldown_seconds}s)")
                return False
        
        # Check absolute threshold (most important!)
        abs_imbalance = abs(imbalance_lots)
        if abs_imbalance < self.min_imbalance_lots:
            return False
        
        # Check percentage threshold
        abs_pct = abs(imbalance_pct)
        if abs_pct < self.min_imbalance_pct:
            return False
        
        # Both thresholds met!
        logger.info(f"🔄 REBALANCE TRIGGERED:")
        logger.info(f"   Imbalance: {imbalance_lots:+.4f} lots ({imbalance_pct:+.2%})")
        logger.info(f"   Threshold: {self.min_imbalance_lots:.4f} lots ({self.min_imbalance_pct:.1%})")
        
        return True
    
    def record_rebalance(self):
        """Record that a rebalance was executed"""
        self.last_rebalance_time = datetime.now()
        self.rebalance_count += 1
        logger.info(f"✅ Rebalance #{self.rebalance_count} recorded at {self.last_rebalance_time}")
    
    def get_rebalance_quantity(self, imbalance_lots: float) -> Dict:
        """
        Calculate how much to trade to rebalance
        
        Args:
            imbalance_lots: Current imbalance
                           +0.012 = Too much secondary (excess)
                           -0.012 = Too little secondary (deficit)
            
        Returns:
            Dict with trade details
            
        Example 1 - Excess secondary:
            Imbalance: +0.012 lots XAG (too much)
            → SELL 0.01 lots XAG to reduce
            
        Example 2 - Deficit secondary:
            Imbalance: -0.012 lots XAG (too little)
            → BUY 0.01 lots XAG to increase
        """
        # Round to nearest 0.01 (MT5 minimum)
        abs_imbalance = abs(imbalance_lots)
        rebalance_qty = round(abs_imbalance / 0.01) * 0.01
        
        # Determine direction:
        # If imbalance > 0 (excess) → SELL to reduce
        # If imbalance < 0 (deficit) → BUY to increase
        if imbalance_lots > 0:
            # Excess - need to SELL
            trade_side = 'SELL'
            trade_qty = -rebalance_qty  # Negative = sell
        else:
            # Deficit - need to BUY
            trade_side = 'BUY'
            trade_qty = rebalance_qty  # Positive = buy
        
        logger.info(f"Rebalance calculation:")
        logger.info(f"  Imbalance: {imbalance_lots:+.4f} lots")
        logger.info(f"  Action: {trade_side} {rebalance_qty:.4f} lots")
        logger.info(f"  After trade: {imbalance_lots + trade_qty:+.4f} lots")
        
        return {
            'imbalance': imbalance_lots,
            'trade_qty': trade_qty,  # Signed quantity
            'trade_volume': rebalance_qty,  # Absolute volume
            'trade_side': trade_side,
            'expected_new_imbalance': imbalance_lots + trade_qty
        }
    
    def get_stats(self) -> Dict:
        """Get rebalancer statistics"""
        if self.last_rebalance_time:
            time_since = (datetime.now() - self.last_rebalance_time).total_seconds()
        else:
            time_since = None
            
        return {
            'rebalance_count': self.rebalance_count,
            'last_rebalance': self.last_rebalance_time,
            'time_since_last': time_since,
            'min_imbalance_lots': self.min_imbalance_lots,
            'min_imbalance_pct': self.min_imbalance_pct,
            'cooldown_seconds': self.cooldown_seconds
        }


def calculate_rebalance_trade(primary_lots: float,
                              secondary_lots: float,
                              target_hedge_ratio: float,
                              min_trade_lots: float = 0.01) -> Optional[Dict]:
    """
    Calculate what trade is needed to rebalance the hedge
    
    Args:
        primary_lots: Current primary position lots (e.g., 0.01 XAU)
        secondary_lots: Current secondary position lots (e.g., 0.0100 XAG)
        target_hedge_ratio: Target ratio (secondary_lots / primary_lots)
        min_trade_lots: Minimum tradeable lots
        
    Returns:
        Dict with rebalance trade details or None if no rebalance needed
        
    Example 1 - Excess secondary (too much):
        primary_lots = 0.01 XAU
        secondary_lots = 0.0100 XAG (MT5 rounded up)
        target_ratio = 0.7179
        
        Ideal secondary = 0.01 × 0.7179 = 0.007179
        Actual secondary = 0.0100
        Imbalance = 0.0100 - 0.007179 = +0.002821 (excess)
        
        If imbalance < 0.01: No trade needed (too small)
        
    Example 2 - Deficit secondary (too little):
        primary_lots = 0.02 XAU
        secondary_lots = 0.01 XAG (MT5 rounded down)
        target_ratio = 0.7179
        
        Ideal secondary = 0.02 × 0.7179 = 0.014358
        Actual secondary = 0.01
        Imbalance = 0.01 - 0.014358 = -0.004358 (deficit)
        
        → Need to BUY 0.01 XAG to reach 0.02
    """
    # Calculate ideal secondary lots
    ideal_secondary = abs(primary_lots) * target_hedge_ratio
    
    # Calculate imbalance (actual - ideal)
    # Positive = excess (too much)
    # Negative = deficit (too little)
    imbalance = secondary_lots - ideal_secondary
    
    # Check if imbalance >= minimum tradeable
    if abs(imbalance) < min_trade_lots:
        return None
    
    # Calculate rebalance quantity (rounded to min_trade_lots)
    abs_imbalance = abs(imbalance)
    rebalance_volume = round(abs_imbalance / min_trade_lots) * min_trade_lots
    
    # Determine direction
    if imbalance > 0:
        # Excess - SELL to reduce
        rebalance_direction = 'SELL'
        rebalance_qty = -rebalance_volume
    else:
        # Deficit - BUY to increase
        rebalance_direction = 'BUY'
        rebalance_qty = rebalance_volume
    
    return {
        'primary_lots': primary_lots,
        'secondary_lots': secondary_lots,
        'ideal_secondary': ideal_secondary,
        'imbalance': imbalance,
        'imbalance_pct': (imbalance / ideal_secondary) if ideal_secondary != 0 else 0,
        'rebalance_qty': rebalance_qty,  # Signed quantity
        'rebalance_volume': rebalance_volume,  # Absolute volume
        'rebalance_direction': rebalance_direction,
        'new_secondary_lots': secondary_lots + rebalance_qty
    }


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create rebalancer
    rebalancer = AutoRebalancer(
        min_imbalance_lots=0.01,
        min_imbalance_pct=0.05,  # 5%
        cooldown_seconds=3600     # 1 hour
    )
    
    # Test scenario 1: Excess secondary (too much)
    print("\n=== Test Scenario 1: EXCESS ===")
    print("Current: 0.01 XAU / 0.0100 XAG")
    print("Target ratio: 0.7179")
    print("Ideal: 0.01 × 0.7179 = 0.007179 XAG")
    print("Actual: 0.0100 XAG (rounded up by MT5)")
    print("Imbalance: +0.002821 (excess)")
    print()
    
    trade1 = calculate_rebalance_trade(
        primary_lots=0.01,
        secondary_lots=0.0100,
        target_hedge_ratio=0.7179
    )
    
    if trade1:
        print("❌ SHOULD NOT REBALANCE - Imbalance < 0.01 lot")
        print(f"  Imbalance: {trade1['imbalance']:+.6f} lots")
    else:
        print("✅ CORRECT - No rebalance (imbalance too small)")
    
    # Test scenario 2: Large excess
    print("\n=== Test Scenario 2: LARGE EXCESS ===")
    print("Current: 0.01 XAU / 0.025 XAG")
    print("Target ratio: 0.7179")
    print("Ideal: 0.01 × 0.7179 = 0.007179 XAG")
    print("Actual: 0.025 XAG (way too much!)")
    print("Imbalance: +0.017821 (excess)")
    print()
    
    trade2 = calculate_rebalance_trade(
        primary_lots=0.01,
        secondary_lots=0.025,
        target_hedge_ratio=0.7179
    )
    
    if trade2:
        print("✅ Rebalance needed!")
        print(f"  Imbalance: {trade2['imbalance']:+.6f} lots ({trade2['imbalance_pct']:+.2%})")
        print(f"  Action: {trade2['rebalance_direction']} {trade2['rebalance_volume']:.4f} lots")
        print(f"  Result: {trade2['new_secondary_lots']:.6f} lots XAG")
        
        # Check if should trigger
        if rebalancer.should_rebalance(trade2['imbalance'], abs(trade2['imbalance_pct'])):
            print("\n✅ EXECUTE REBALANCE!")
            rebalancer.record_rebalance()
    
    # Test scenario 3: Deficit (too little)
    print("\n=== Test Scenario 3: DEFICIT ===")
    print("Current: 0.02 XAU / 0.01 XAG")
    print("Target ratio: 0.7179")
    print("Ideal: 0.02 × 0.7179 = 0.014358 XAG")
    print("Actual: 0.01 XAG (too little!)")
    print("Imbalance: -0.004358 (deficit)")
    print()
    
    trade3 = calculate_rebalance_trade(
        primary_lots=0.02,
        secondary_lots=0.01,
        target_hedge_ratio=0.7179
    )
    
    if trade3:
        print("❌ SHOULD NOT REBALANCE - Imbalance < 0.01 lot")
        print(f"  Imbalance: {trade3['imbalance']:+.6f} lots")
    else:
        print("✅ CORRECT - No rebalance (imbalance too small)")
    
    # Test scenario 4: Large deficit
    print("\n=== Test Scenario 4: LARGE DEFICIT ===")
    print("Current: 0.05 XAU / 0.02 XAG")
    print("Target ratio: 0.7179")
    print("Ideal: 0.05 × 0.7179 = 0.035895 XAG")
    print("Actual: 0.02 XAG (way too little!)")
    print("Imbalance: -0.015895 (deficit)")
    print()
    
    trade4 = calculate_rebalance_trade(
        primary_lots=0.05,
        secondary_lots=0.02,
        target_hedge_ratio=0.7179
    )
    
    if trade4:
        print("✅ Rebalance needed!")
        print(f"  Imbalance: {trade4['imbalance']:+.6f} lots ({trade4['imbalance_pct']:+.2%})")
        print(f"  Action: {trade4['rebalance_direction']} {trade4['rebalance_volume']:.4f} lots")
        print(f"  Result: {trade4['new_secondary_lots']:.6f} lots XAG")
        
        # Check if should trigger
        if rebalancer.should_rebalance(abs(trade4['imbalance']), abs(trade4['imbalance_pct'])):
            print("\n✅ EXECUTE REBALANCE!")
