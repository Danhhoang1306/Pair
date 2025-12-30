"""
Position Rebalancing System
Automatically scale into positions as spread widens

Features:
- Scale-in at z-score intervals
- Track entry levels
- Maintain hedge ratio
- Risk management
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RebalanceLevel:
    """Rebalance entry level"""
    zscore: float
    executed: bool
    timestamp: Optional[datetime] = None
    gold_lots: float = 0.0
    silver_lots: float = 0.0
    
    def __str__(self):
        status = "✓" if self.executed else "○"
        return f"[{status}] z={self.zscore:.2f}"


class PositionRebalancer:
    """
    Manage position rebalancing based on z-score changes
    
    Strategy:
    - Initial entry: z = -2.0 (LONG) or +2.0 (SHORT)
    - Scale in: Every 0.5 z-score unit
    - Max entries: Stop at z = -3.0 (or +3.0)
    
    Example (LONG SPREAD):
    Entry 1: z = -2.0 → 33% position
    Entry 2: z = -2.5 → 33% position (total 66%)
    Entry 3: z = -3.0 → 34% position (total 100%, stop loss)
    """
    
    def __init__(self,
                 scale_interval: float = 0.5,
                 max_zscore: float = 3.0,
                 initial_fraction: float = 0.33):
        """
        Initialize rebalancer
        
        Args:
            scale_interval: Z-score interval for scaling (e.g., 0.5)
            max_zscore: Maximum z-score (stop loss level)
            initial_fraction: Fraction of position for first entry
        """
        self.scale_interval = scale_interval
        self.max_zscore = max_zscore
        self.initial_fraction = initial_fraction
        
        # Active positions tracking
        self.active_positions: Dict[str, Dict] = {}  # spread_id -> position data
        
        logger.info(f"PositionRebalancer initialized "
                   f"(interval={scale_interval}, max_z={max_zscore}, "
                   f"initial_frac={initial_fraction})")
    
    def calculate_rebalance_levels(self, 
                                   initial_zscore: float,
                                   side: str) -> List[RebalanceLevel]:
        """
        Calculate all potential rebalance levels
        
        Args:
            initial_zscore: Entry z-score
            side: 'LONG' or 'SHORT'
            
        Returns:
            List of RebalanceLevel
        """
        levels = []
        
        if side == 'LONG':
            # LONG SPREAD: z < -2.0
            # Scale in as z goes MORE negative
            current_z = initial_zscore
            
            while abs(current_z) < self.max_zscore:
                levels.append(RebalanceLevel(
                    zscore=current_z,
                    executed=(current_z == initial_zscore)  # First level executed
                ))
                current_z -= self.scale_interval
            
            # Add final level at stop loss
            levels.append(RebalanceLevel(
                zscore=-self.max_zscore,
                executed=False
            ))
            
        else:  # SHORT
            # SHORT SPREAD: z > +2.0
            # Scale in as z goes MORE positive
            current_z = initial_zscore
            
            while abs(current_z) < self.max_zscore:
                levels.append(RebalanceLevel(
                    zscore=current_z,
                    executed=(current_z == initial_zscore)
                ))
                current_z += self.scale_interval
            
            # Add final level at stop loss
            levels.append(RebalanceLevel(
                zscore=self.max_zscore,
                executed=False
            ))
        
        return levels
    
    def register_position(self,
                         spread_id: str,
                         side: str,
                         entry_zscore: float,
                         total_position_size: float) -> Dict:
        """
        Register new position for rebalancing
        
        Args:
            spread_id: Unique spread identifier
            side: 'LONG' or 'SHORT'
            entry_zscore: Initial entry z-score
            total_position_size: Total planned position size (100%)
            
        Returns:
            Position data
        """
        # Calculate rebalance levels
        levels = self.calculate_rebalance_levels(entry_zscore, side)
        
        # Calculate position size per level
        num_levels = len(levels)
        size_per_level = total_position_size / num_levels
        
        # Mark first level as executed
        levels[0].executed = True
        levels[0].timestamp = datetime.now()
        
        position_data = {
            'spread_id': spread_id,
            'side': side,
            'entry_zscore': entry_zscore,
            'total_position_size': total_position_size,
            'size_per_level': size_per_level,
            'levels': levels,
            'total_executed': 1,
            'remaining_size': total_position_size - size_per_level
        }
        
        self.active_positions[spread_id] = position_data
        
        logger.info(f"Registered position {spread_id[:8]} for rebalancing:")
        logger.info(f"  Side: {side}")
        logger.info(f"  Entry z-score: {entry_zscore:.2f}")
        logger.info(f"  Total size: {total_position_size:.2%}")
        logger.info(f"  Levels: {num_levels} (size per level: {size_per_level:.2%})")
        logger.info(f"  Rebalance points: {[l.zscore for l in levels]}")
        
        return position_data
    
    def check_rebalance_needed(self,
                              spread_id: str,
                              current_zscore: float) -> Optional[Dict]:
        """
        Check if rebalancing is needed
        
        Args:
            spread_id: Spread identifier
            current_zscore: Current z-score
            
        Returns:
            Rebalance instruction or None
        """
        if spread_id not in self.active_positions:
            return None
        
        position = self.active_positions[spread_id]
        side = position['side']
        levels = position['levels']
        
        # Find next unexecuted level that should be triggered
        for level in levels:
            if level.executed:
                continue
            
            # Check if level should be triggered
            should_trigger = False
            
            if side == 'LONG':
                # LONG: trigger when z goes MORE negative
                should_trigger = current_zscore <= level.zscore
            else:  # SHORT
                # SHORT: trigger when z goes MORE positive
                should_trigger = current_zscore >= level.zscore
            
            if should_trigger:
                logger.info(f"[REBALANCE] Position {spread_id[:8]} needs rebalancing!")
                logger.info(f"  Current z-score: {current_zscore:.2f}")
                logger.info(f"  Trigger level: {level.zscore:.2f}")
                logger.info(f"  Side: {side}")
                
                return {
                    'spread_id': spread_id,
                    'side': side,
                    'level': level,
                    'position_size': position['size_per_level'],
                    'current_zscore': current_zscore,
                    'reason': f"z-score reached {level.zscore:.2f}"
                }
        
        return None
    
    def mark_level_executed(self,
                           spread_id: str,
                           zscore: float,
                           gold_lots: float,
                           silver_lots: float):
        """
        Mark rebalance level as executed
        
        Args:
            spread_id: Spread identifier
            zscore: Z-score level executed
            gold_lots: Gold lots added
            silver_lots: Silver lots added
        """
        if spread_id not in self.active_positions:
            logger.error(f"Spread {spread_id} not found")
            return
        
        position = self.active_positions[spread_id]
        
        for level in position['levels']:
            if abs(level.zscore - zscore) < 0.01:
                level.executed = True
                level.timestamp = datetime.now()
                level.gold_lots = gold_lots
                level.silver_lots = silver_lots
                
                position['total_executed'] += 1
                position['remaining_size'] -= position['size_per_level']
                
                logger.info(f"[SUCCESS] Rebalance executed for {spread_id[:8]}")
                logger.info(f"  Level: {level.zscore:.2f}")
                logger.info(f"  Added: {gold_lots:.4f} Gold, {silver_lots:.4f} Silver")
                logger.info(f"  Progress: {position['total_executed']}/{len(position['levels'])} levels")
                break
    
    def remove_position(self, spread_id: str):
        """Remove position from tracking"""
        if spread_id in self.active_positions:
            del self.active_positions[spread_id]
            logger.info(f"Removed position {spread_id[:8]} from rebalancer")
    
    def get_position_status(self, spread_id: str) -> Optional[str]:
        """Get formatted position status"""
        if spread_id not in self.active_positions:
            return None
        
        position = self.active_positions[spread_id]
        levels = position['levels']
        
        status_lines = [
            f"Position {spread_id[:8]} ({position['side']}):",
            f"  Entry: z={position['entry_zscore']:.2f}",
            f"  Progress: {position['total_executed']}/{len(levels)} levels",
            f"  Levels:"
        ]
        
        for level in levels:
            status_lines.append(f"    {level}")
        
        return "\n".join(status_lines)
    
    def get_all_positions_status(self) -> str:
        """Get status of all active positions"""
        if not self.active_positions:
            return "No active positions being rebalanced"
        
        status_lines = ["=== REBALANCING STATUS ==="]
        
        for spread_id in self.active_positions:
            status_lines.append(self.get_position_status(spread_id))
            status_lines.append("")
        
        return "\n".join(status_lines)
