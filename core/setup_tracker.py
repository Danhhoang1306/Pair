"""
Setup Tracker - Track positions by strategy setup rather than individual spreads
Each setup can have multiple positions from pyramiding
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SetupPosition:
    """Single position within a setup"""
    spread_id: str
    short_id: str  # Short ID used in MT5 comment (e.g., "175430")
    mt5_primary_ticket: int
    mt5_secondary_ticket: int
    entry_zscore: float
    primary_lots: float
    secondary_lots: float
    level: str  # 'initial', 'pyramid_1', 'pyramid_2', etc.
    timestamp: str


@dataclass
class Setup:
    """A trading setup - may contain multiple positions from pyramiding"""
    setup_id: str
    entry_time: str
    entry_zscore: float
    exit_zscore: Optional[float]
    side: str  # 'LONG' or 'SHORT'
    pair: str  # 'BTC/ETH', 'XAU/XAG'
    entry_hedge_ratio: float
    positions: List[SetupPosition]
    status: str  # 'ACTIVE', 'CLOSED', 'PARTIAL'
    last_updated: str
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization"""
        return {
            'setup_id': self.setup_id,
            'entry_time': self.entry_time,
            'entry_zscore': self.entry_zscore,
            'exit_zscore': self.exit_zscore,
            'side': self.side,
            'pair': self.pair,
            'entry_hedge_ratio': self.entry_hedge_ratio,
            'positions': [asdict(p) for p in self.positions],
            'status': self.status,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Setup':
        """Load from dict"""
        positions = [SetupPosition(**p) for p in data.get('positions', [])]
        return cls(
            setup_id=data['setup_id'],
            entry_time=data['entry_time'],
            entry_zscore=data['entry_zscore'],
            exit_zscore=data.get('exit_zscore'),
            side=data['side'],
            pair=data['pair'],
            entry_hedge_ratio=data['entry_hedge_ratio'],
            positions=positions,
            status=data.get('status', 'ACTIVE'),
            last_updated=data.get('last_updated', datetime.now().isoformat())
        )


class SetupTracker:
    """
    Track positions by setup (strategy entry) rather than individual spreads
    
    Each setup can have multiple positions from pyramiding.
    Simplifies recovery: just need to check if setup's positions still exist in MT5.
    """
    
    def __init__(self, positions_dir: str = 'positions'):
        self.positions_dir = Path(positions_dir)
        self.positions_dir.mkdir(exist_ok=True)
        
        self.setups_file = self.positions_dir / 'setups.json'
        self.active_setups: Dict[str, Setup] = {}
        
        # Load existing setups
        self._load_setups()
        
        logger.info(f"SetupTracker initialized (dir={positions_dir})")
        logger.info(f"  Active setups: {len(self.active_setups)}")
    
    def _load_setups(self):
        """Load all active setups from disk"""
        if not self.setups_file.exists():
            logger.info("No existing setups file")
            return
        
        try:
            with open(self.setups_file, 'r') as f:
                data = json.load(f)
            
            # Load each setup's detail file
            for setup_id in data.get('active_setups', {}):
                setup_file = self.positions_dir / f"{setup_id}.json"
                if setup_file.exists():
                    with open(setup_file, 'r') as f:
                        setup_data = json.load(f)
                    self.active_setups[setup_id] = Setup.from_dict(setup_data)
                    logger.info(f"  Loaded setup: {setup_id} ({len(setup_data['positions'])} positions)")
        
        except Exception as e:
            logger.error(f"Failed to load setups: {e}")
    
    def _save_setups(self):
        """Save master setups index"""
        try:
            master_data = {
                'active_setups': {
                    sid: {
                        'entry_time': s.entry_time,
                        'entry_zscore': s.entry_zscore,
                        'side': s.side,
                        'pair': s.pair,
                        'total_positions': len(s.positions),
                        'status': s.status
                    }
                    for sid, s in self.active_setups.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.setups_file, 'w') as f:
                json.dump(master_data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save setups index: {e}")
    
    def _save_setup(self, setup: Setup):
        """Save individual setup to its detail file"""
        try:
            setup_file = self.positions_dir / f"{setup.setup_id}.json"
            with open(setup_file, 'w') as f:
                json.dump(setup.to_dict(), f, indent=2)
            
            # Update master index
            self._save_setups()
        
        except Exception as e:
            logger.error(f"Failed to save setup {setup.setup_id}: {e}")
    
    def create_setup(self,
                    entry_zscore: float,
                    side: str,
                    pair: str,
                    entry_hedge_ratio: float) -> str:
        """
        Create a new setup (strategy entry)
        
        Returns:
            setup_id
        """
        # Generate setup ID from timestamp
        setup_id = f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        setup = Setup(
            setup_id=setup_id,
            entry_time=datetime.now().isoformat(),
            entry_zscore=entry_zscore,
            exit_zscore=None,
            side=side,
            pair=pair,
            entry_hedge_ratio=entry_hedge_ratio,
            positions=[],
            status='ACTIVE',
            last_updated=datetime.now().isoformat()
        )
        
        self.active_setups[setup_id] = setup
        self._save_setup(setup)
        
        logger.info(f"Created setup: {setup_id} (z={entry_zscore:.2f}, {side}, {pair})")
        return setup_id
    
    def add_position_to_setup(self,
                             setup_id: str,
                             spread_id: str,
                             short_id: str,  # Short ID for MT5 comment
                             mt5_primary_ticket: int,
                             mt5_secondary_ticket: int,
                             entry_zscore: float,
                             primary_lots: float,
                             secondary_lots: float,
                             level: str = 'initial'):
        """Add a position to an existing setup"""
        if setup_id not in self.active_setups:
            logger.error(f"Setup not found: {setup_id}")
            return
        
        setup = self.active_setups[setup_id]
        
        position = SetupPosition(
            spread_id=spread_id,
            short_id=short_id,
            mt5_primary_ticket=mt5_primary_ticket,
            mt5_secondary_ticket=mt5_secondary_ticket,
            entry_zscore=entry_zscore,
            primary_lots=primary_lots,
            secondary_lots=secondary_lots,
            level=level,
            timestamp=datetime.now().isoformat()
        )
        
        setup.positions.append(position)
        setup.last_updated = datetime.now().isoformat()
        
        self._save_setup(setup)
        
        logger.info(f"Added position to {setup_id}: {spread_id} (MT5: ID:{short_id}, {level})")
    
    def get_active_setups(self) -> List[Setup]:
        """Get all active setups"""
        return [s for s in self.active_setups.values() if s.status == 'ACTIVE']
    
    def get_setup_positions(self, setup_id: str) -> List[SetupPosition]:
        """Get all positions in a setup"""
        if setup_id not in self.active_setups:
            return []
        return self.active_setups[setup_id].positions
    
    def close_setup(self, setup_id: str, exit_zscore: float):
        """Mark setup as closed"""
        if setup_id not in self.active_setups:
            logger.error(f"Setup not found: {setup_id}")
            return
        
        setup = self.active_setups[setup_id]
        setup.status = 'CLOSED'
        setup.exit_zscore = exit_zscore
        setup.last_updated = datetime.now().isoformat()
        
        self._save_setup(setup)
        
        # Remove from active (but keep file for history)
        del self.active_setups[setup_id]
        self._save_setups()
        
        logger.info(f"Closed setup: {setup_id} ({len(setup.positions)} positions)")
    
    def verify_setup_on_mt5(self, setup_id: str, mt5_connector) -> Tuple[bool, List[int]]:
        """
        Verify if setup's positions still exist on MT5
        
        Returns:
            (all_found, missing_tickets)
        """
        if setup_id not in self.active_setups:
            return False, []
        
        setup = self.active_setups[setup_id]
        missing = []
        
        # Get all MT5 positions
        import MetaTrader5 as mt5
        mt5_positions = mt5.positions_get()
        if mt5_positions is None:
            mt5_positions = []
        
        mt5_tickets = {p.ticket for p in mt5_positions}
        
        # Check each position in setup
        for pos in setup.positions:
            if pos.mt5_primary_ticket not in mt5_tickets:
                missing.append(pos.mt5_primary_ticket)
            if pos.mt5_secondary_ticket not in mt5_tickets:
                missing.append(pos.mt5_secondary_ticket)
        
        all_found = len(missing) == 0
        
        if all_found:
            logger.info(f"✓ Setup {setup_id}: All {len(setup.positions)*2} positions found on MT5")
        else:
            logger.warning(f"✗ Setup {setup_id}: {len(missing)} positions MISSING on MT5")
            logger.warning(f"  Missing tickets: {missing}")
        
        return all_found, missing
    
    def get_all_setup_tickets(self, setup_id: str) -> List[int]:
        """Get all MT5 tickets for a setup"""
        if setup_id not in self.active_setups:
            return []
        
        setup = self.active_setups[setup_id]
        tickets = []
        
        for pos in setup.positions:
            tickets.append(pos.mt5_primary_ticket)
            tickets.append(pos.mt5_secondary_ticket)
        
        return tickets
