"""
Hybrid Rebalancing System
Combines pyramiding (scale-in) with dynamic hedge adjustment

Features:
1. Pyramiding: Add positions when spread widens
2. Hedge Adjustment: Maintain hedge ratio as it changes
3. Threshold-based: Only adjust when drift > threshold
4. Time-gated: Prevent overtrading
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RebalanceLevel:
    """Pyramiding level"""
    zscore: float
    executed: bool
    timestamp: Optional[datetime] = None
    gold_lots: float = 0.0
    silver_lots: float = 0.0
    
    def __str__(self):
        status = "✓" if self.executed else "○"
        return f"[{status}] z={self.zscore:.2f}"


@dataclass
class HedgeAdjustment:
    """Hedge adjustment action"""
    spread_id: str
    symbol: str
    action: str  # 'BUY' or 'SELL'
    quantity: float
    reason: str
    old_hedge: float
    new_hedge: float
    drift_pct: float


class HybridRebalancer:
    """
    Advanced rebalancing with:
    1. Pyramiding (scale-in on z-score triggers)
    2. Dynamic hedge adjustment (maintain dollar neutrality)
    
    Configuration:
    - Pyramiding: z-score intervals
    - Hedge drift threshold: Minimum drift % to trigger adjustment
    - Time gate: Minimum time between adjustments
    """
    
    def __init__(self,
                 # Pyramiding config
                 scale_interval: float = 0.5,
                 max_zscore: float = 3.0,
                 initial_fraction: float = 0.33,
                 
                 # Hedge adjustment config
                 hedge_drift_threshold: float = 0.05,  # 5%
                 min_absolute_drift: float = 0.01,     # 0.01 lots
                 min_adjustment_interval: int = 3600,   # 1 hour
                 enable_hedge_adjustment: bool = True):
        """
        Initialize hybrid rebalancer
        
        Args:
            scale_interval: Z-score interval for pyramiding
            max_zscore: Maximum z-score (stop loss)
            initial_fraction: First entry size
            hedge_drift_threshold: Minimum drift % to adjust (e.g., 0.05 = 5%)
            min_absolute_drift: Minimum absolute drift in lots (e.g., 0.01)
            min_adjustment_interval: Min seconds between adjustments
            enable_hedge_adjustment: Enable/disable hedge adjustment
        """
        # Pyramiding
        self.scale_interval = scale_interval
        self.max_zscore = max_zscore
        self.initial_fraction = initial_fraction
        
        # Hedge adjustment
        self.hedge_drift_threshold = hedge_drift_threshold
        self.min_absolute_drift = min_absolute_drift
        self.min_adjustment_interval = min_adjustment_interval
        self.enable_hedge_adjustment = enable_hedge_adjustment
        
        # Tracking
        self.active_positions: Dict[str, Dict] = {}
        self.last_adjustment: Dict[str, float] = {}  # spread_id -> timestamp
        self.adjustment_history: List[HedgeAdjustment] = []
        
        logger.info(f"HybridRebalancer initialized:")
        logger.info(f"  Pyramiding: interval={scale_interval}, max_z={max_zscore}")
        logger.info(f"  Hedge adjustment: threshold={hedge_drift_threshold:.1%}, "
                   f"absolute={min_absolute_drift} lots, "
                   f"interval={min_adjustment_interval}s, enabled={enable_hedge_adjustment}")
    
    def calculate_pyramiding_levels(self,
                                    initial_zscore: float,
                                    side: str) -> List[RebalanceLevel]:
        """Calculate pyramiding levels (same as before)"""
        levels = []
        
        if side == 'LONG':
            current_z = initial_zscore
            while abs(current_z) < self.max_zscore:
                levels.append(RebalanceLevel(
                    zscore=current_z,
                    executed=(current_z == initial_zscore)
                ))
                current_z -= self.scale_interval
            
            levels.append(RebalanceLevel(
                zscore=-self.max_zscore,
                executed=False
            ))
        else:  # SHORT
            current_z = initial_zscore
            while abs(current_z) < self.max_zscore:
                levels.append(RebalanceLevel(
                    zscore=current_z,
                    executed=(current_z == initial_zscore)
                ))
                current_z += self.scale_interval
            
            levels.append(RebalanceLevel(
                zscore=self.max_zscore,
                executed=False
            ))
        
        return levels
    
    def register_position(self,
                         spread_id: str,
                         side: str,
                         entry_zscore: float,
                         entry_hedge_ratio: float,
                         gold_lots: float,
                         silver_lots: float,
                         total_position_size: float,
                         primary_symbol: str = 'XAUUSD',
                         secondary_symbol: str = 'XAGUSD') -> Dict:
        """
        Register position for both pyramiding and hedge adjustment
        
        Args:
            spread_id: Unique identifier
            side: 'LONG' or 'SHORT'
            entry_zscore: Entry z-score
            entry_hedge_ratio: Hedge ratio at entry
            gold_lots: Actual primary lots
            silver_lots: Actual secondary lots
            total_position_size: Planned total size (100%)
            primary_symbol: Primary symbol (e.g., BTCUSD, XAUUSD)
            secondary_symbol: Secondary symbol (e.g., ETHUSD, XAGUSD)
        """
        levels = self.calculate_pyramiding_levels(entry_zscore, side)
        
        # Mark first level executed
        levels[0].executed = True
        levels[0].timestamp = datetime.now()
        levels[0].gold_lots = gold_lots
        levels[0].silver_lots = silver_lots
        
        position_data = {
            'spread_id': spread_id,
            'side': side,
            'entry_zscore': entry_zscore,
            'entry_hedge_ratio': entry_hedge_ratio,
            'current_hedge_ratio': entry_hedge_ratio,  # Will be updated
            'gold_lots': gold_lots,
            'silver_lots': silver_lots,
            'total_position_size': total_position_size,
            'size_per_level': total_position_size / len(levels),
            'levels': levels,
            'total_executed': 1,
            'entry_time': datetime.now(),
            'last_adjustment_time': None,
            'primary_symbol': primary_symbol,  # NEW!
            'secondary_symbol': secondary_symbol  # NEW!
        }
        
        self.active_positions[spread_id] = position_data
        self.last_adjustment[spread_id] = time.time()
        
        logger.info(f"[HYBRID] Position {spread_id[:8]} registered")
        logger.info(f"  Symbols: {primary_symbol}/{secondary_symbol}")
        logger.info(f"  Pyramiding levels: {len(levels)}")
        logger.info(f"  Entry hedge ratio: {entry_hedge_ratio:.4f}")
        logger.info(f"  Primary: {gold_lots:.4f} lots, Secondary: {silver_lots:.4f} lots")
        
        return position_data
    
    def check_pyramiding(self,
                        spread_id: str,
                        current_zscore: float) -> Optional[Dict]:
        """
        Check if pyramiding (scale-in) is needed
        Same logic as before
        """
        if spread_id not in self.active_positions:
            return None
        
        position = self.active_positions[spread_id]
        side = position['side']
        levels = position['levels']
        
        # Find next unexecuted level
        for level in levels:
            if level.executed:
                continue
            
            should_trigger = False
            
            if side == 'LONG':
                should_trigger = current_zscore <= level.zscore
            else:  # SHORT
                should_trigger = current_zscore >= level.zscore
            
            if should_trigger:
                logger.info(f"[PYRAMIDING] Position {spread_id[:8]} scale-in triggered!")
                logger.info(f"  Current z: {current_zscore:.2f}")
                logger.info(f"  Trigger level: {level.zscore:.2f}")
                
                return {
                    'type': 'PYRAMIDING',
                    'spread_id': spread_id,
                    'side': side,
                    'level': level,
                    'position_size': position['size_per_level'],
                    'current_zscore': current_zscore,
                    'reason': f"Pyramiding: z-score reached {level.zscore:.2f}"
                }
        
        return None
    
    def check_hedge_drift(self,
                         spread_id: str,
                         current_hedge_ratio: float) -> Optional[HedgeAdjustment]:
        """
        Check if hedge adjustment is needed
        
        Strategy: Always adjust the SMALLER side to minimize exposure changes
        - If secondary < target: BUY secondary
        - If secondary > target: BUY primary (instead of selling secondary)
        
        Only adjust if:
        1. Hedge adjustment is enabled
        2. Drift > threshold
        3. Enough time since last adjustment
        4. Position still open
        """
        # DEBUG: Always log check attempt
        logger.debug(f"[HEDGE CHECK] Checking drift for {spread_id[:8]}")
        
        if not self.enable_hedge_adjustment:
            logger.debug(f"[HEDGE CHECK] Disabled for {spread_id[:8]}")
            return None
        
        if spread_id not in self.active_positions:
            logger.debug(f"[HEDGE CHECK] Position {spread_id[:8]} not in active_positions")
            return None
        
        position = self.active_positions[spread_id]
        
        # Check time gate
        last_adj = self.last_adjustment.get(spread_id, 0)
        time_since_last = time.time() - last_adj
        
        if time_since_last < self.min_adjustment_interval:
            logger.debug(f"[HEDGE CHECK] Too soon for {spread_id[:8]}: {time_since_last:.0f}s < {self.min_adjustment_interval}s")
            return None
        
        # Get current position sizes
        primary_lots = position['gold_lots']
        secondary_lots = position['silver_lots']
        
        # Calculate target secondary based on current primary
        target_secondary_lots = primary_lots * current_hedge_ratio
        
        if target_secondary_lots == 0:
            logger.debug(f"[HEDGE CHECK] Target secondary is 0 for {spread_id[:8]}")
            return None
        
        # Calculate drift
        drift = target_secondary_lots - secondary_lots
        drift_pct = abs(drift) / target_secondary_lots
        abs_drift = abs(drift)
        
        # DEBUG: Always log drift calculation
        logger.info(f"[HEDGE CHECK] Position {spread_id[:8]}:")
        logger.info(f"  Primary: {primary_lots:.4f} lots")
        logger.info(f"  Current secondary: {secondary_lots:.4f} lots")
        logger.info(f"  Target secondary: {target_secondary_lots:.4f} lots")
        logger.info(f"  Drift: {drift_pct:.2%} ({abs_drift:.4f} lots)")
        logger.info(f"  Thresholds: {self.hedge_drift_threshold:.2%} OR {self.min_absolute_drift:.4f} lots")
        
        # DUAL THRESHOLD CHECK:
        # Rebalance if EITHER condition is met:
        # 1. Percentage drift >= threshold (e.g., 5%)
        # 2. Absolute drift >= min lots (e.g., 0.01)
        percentage_exceeded = drift_pct >= self.hedge_drift_threshold
        absolute_exceeded = abs_drift >= self.min_absolute_drift
        
        logger.info(f"  Percentage check: {drift_pct:.2%} >= {self.hedge_drift_threshold:.2%}? {percentage_exceeded}")
        logger.info(f"  Absolute check: {abs_drift:.4f} >= {self.min_absolute_drift:.4f}? {absolute_exceeded}")
        
        if not percentage_exceeded and not absolute_exceeded:
            logger.info(f"  → No adjustment needed")
            return None
        
        logger.info(f"  → ADJUSTMENT NEEDED!")
        
        # Determine which side to adjust
        old_hedge = position['current_hedge_ratio']
        
        if drift > 0:
            # Secondary is SHORT → Need MORE secondary
            adjust_symbol = position.get('secondary_symbol', 'XAGUSD')
            adjust_action = 'BUY'
            adjust_quantity = abs_drift
            reason = f"Secondary short by {abs_drift:.4f} lots ({drift_pct:.2%})"
        else:
            # Secondary is LONG → Need LESS secondary
            # We choose to BUY primary to maintain/increase position size
            adjust_symbol = position.get('primary_symbol', 'XAUUSD')
            adjust_action = 'BUY'
            adjust_quantity = abs_drift / current_hedge_ratio
            reason = f"Secondary long by {abs_drift:.4f} lots ({drift_pct:.2%}), buying primary"
        
        logger.info(f"[HEDGE DRIFT] Position {spread_id[:8]} needs adjustment")
        logger.info(f"  Old hedge: {old_hedge:.4f} → New hedge: {current_hedge_ratio:.4f}")
        logger.info(f"  Primary: {primary_lots:.4f} lots")
        logger.info(f"  Current secondary: {secondary_lots:.4f} lots")
        logger.info(f"  Target secondary: {target_secondary_lots:.4f} lots")
        logger.info(f"  Drift: {drift_pct:.2%} ({abs_drift:.4f} lots)")
        logger.info(f"  → Action: {adjust_action} {adjust_quantity:.4f} lots of {adjust_symbol}")
        
        # Log which threshold triggered
        if percentage_exceeded:
            logger.info(f"  ✓ Percentage threshold: {drift_pct:.2%} >= {self.hedge_drift_threshold:.2%}")
        if absolute_exceeded:
            logger.info(f"  ✓ Absolute threshold: {abs_drift:.4f} >= {self.min_absolute_drift:.4f} lots")
        
        adjustment = HedgeAdjustment(
            spread_id=spread_id,
            symbol=adjust_symbol,
            action=adjust_action,
            quantity=adjust_quantity,
            reason=reason,
            old_hedge=old_hedge,
            new_hedge=current_hedge_ratio,
            drift_pct=drift_pct
        )
        
        return adjustment
    
    def check_all_rebalancing(self,
                             current_zscore: float,
                             current_hedge_ratio: float) -> Tuple[List[Dict], List[HedgeAdjustment]]:
        """
        Check both pyramiding AND hedge adjustments for all positions
        
        Returns:
            (pyramiding_actions, hedge_adjustments)
        """
        pyramiding_actions = []
        hedge_adjustments = []
        
        for spread_id in list(self.active_positions.keys()):
            # Check pyramiding
            pyramid_action = self.check_pyramiding(spread_id, current_zscore)
            if pyramid_action:
                pyramiding_actions.append(pyramid_action)
            
            # Check hedge drift
            hedge_action = self.check_hedge_drift(spread_id, current_hedge_ratio)
            if hedge_action:
                hedge_adjustments.append(hedge_action)
        
        return pyramiding_actions, hedge_adjustments
    
    def mark_pyramiding_executed(self,
                                 spread_id: str,
                                 zscore: float,
                                 gold_lots: float,
                                 silver_lots: float):
        """Mark pyramiding level as executed"""
        if spread_id not in self.active_positions:
            return
        
        position = self.active_positions[spread_id]
        
        # Find and mark level
        for level in position['levels']:
            if abs(level.zscore - zscore) < 0.01:
                level.executed = True
                level.timestamp = datetime.now()
                level.gold_lots = gold_lots
                level.silver_lots = silver_lots
                break
        
        # Update totals
        position['gold_lots'] += gold_lots
        position['silver_lots'] += silver_lots
        position['total_executed'] += 1
        
        logger.info(f"[PYRAMIDING] Level executed for {spread_id[:8]}")
        logger.info(f"  Total: {position['gold_lots']:.4f} Gold, "
                   f"{position['silver_lots']:.4f} Silver")
    
    def mark_hedge_adjusted(self,
                           spread_id: str,
                           adjustment: HedgeAdjustment,
                           executed_quantity: float):
        """Mark hedge adjustment as executed"""
        if spread_id not in self.active_positions:
            return
        
        position = self.active_positions[spread_id]
        
        # Update position
        if adjustment.action == 'BUY':
            position['silver_lots'] += executed_quantity
        else:  # SELL
            position['silver_lots'] -= executed_quantity
        
        position['current_hedge_ratio'] = adjustment.new_hedge
        position['last_adjustment_time'] = datetime.now()
        
        # Update tracking
        self.last_adjustment[spread_id] = time.time()
        self.adjustment_history.append(adjustment)
        
        logger.info(f"[HEDGE ADJUSTMENT] Executed for {spread_id[:8]}")
        logger.info(f"  {adjustment.action} {executed_quantity:.4f} lots Silver")
        logger.info(f"  New total: {position['silver_lots']:.4f} Silver")
        logger.info(f"  New hedge ratio: {adjustment.new_hedge:.4f}")
    
    def remove_position(self, spread_id: str):
        """Remove position from tracking"""
        if spread_id in self.active_positions:
            del self.active_positions[spread_id]
        if spread_id in self.last_adjustment:
            del self.last_adjustment[spread_id]
        
        logger.info(f"[HYBRID] Position {spread_id[:8]} removed")
    
    def get_statistics(self) -> Dict:
        """Get rebalancing statistics"""
        total_positions = len(self.active_positions)
        total_adjustments = len(self.adjustment_history)
        
        if total_adjustments > 0:
            avg_drift = sum(a.drift_pct for a in self.adjustment_history) / total_adjustments
        else:
            avg_drift = 0.0
        
        return {
            'active_positions': total_positions,
            'total_adjustments': total_adjustments,
            'avg_drift_pct': avg_drift,
            'adjustment_enabled': self.enable_hedge_adjustment,
            'drift_threshold': self.hedge_drift_threshold
        }
