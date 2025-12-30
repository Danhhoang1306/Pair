"""
Simplified Trading Settings
Single global config for ALL pairs - no duplication!
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TradingSettings:
    """
    Global trading settings - applies to ALL pairs!
    No per-pair duplication - just ONE set of settings.
    """
    # Trading parameters
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    stop_loss_zscore: float = 3.5
    max_positions: int = 10
    volume_multiplier: float = 1.0
    
    # Model parameters
    rolling_window_size: int = 200
    update_interval: int = 60
    hedge_drift_threshold: float = 0.05
    
    # Risk parameters
    max_position_pct: float = 20.0
    max_risk_pct: float = 2.0
    max_drawdown_pct: float = 20.0
    daily_loss_limit: float = 5000.0
    
    # Rebalancer parameters
    scale_interval: float = 0.5
    initial_fraction: float = 0.33
    min_adjustment_interval: int = 3600
    
    # Feature flags
    enable_pyramiding: bool = True
    enable_hedge_adjustment: bool = True
    enable_regime_filter: bool = False
    
    # System parameters
    magic_number: int = 234000
    zscore_history_size: int = 200
    position_data_dir: str = "positions"
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_config_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to structured config for YAML"""
        return {
            'trading': {
                'entry_threshold': self.entry_threshold,
                'exit_threshold': self.exit_threshold,
                'stop_loss_zscore': self.stop_loss_zscore,
                'max_positions': self.max_positions,
                'volume_multiplier': self.volume_multiplier
            },
            'model': {
                'rolling_window_size': self.rolling_window_size,
                'update_interval': self.update_interval,
                'hedge_drift_threshold': self.hedge_drift_threshold
            },
            'risk': {
                'max_position_pct': self.max_position_pct,
                'max_risk_pct': self.max_risk_pct,
                'max_drawdown_pct': self.max_drawdown_pct,
                'daily_loss_limit': self.daily_loss_limit
            },
            'rebalancer': {
                'scale_interval': self.scale_interval,
                'initial_fraction': self.initial_fraction,
                'min_adjustment_interval': self.min_adjustment_interval
            },
            'features': {
                'enable_pyramiding': self.enable_pyramiding,
                'enable_hedge_adjustment': self.enable_hedge_adjustment,
                'enable_regime_filter': self.enable_regime_filter
            },
            'system': {
                'magic_number': self.magic_number,
                'zscore_history_size': self.zscore_history_size,
                'position_data_dir': self.position_data_dir,
                'log_level': self.log_level
            }
        }
    
    @classmethod
    def from_config_dict(cls, config: Dict[str, Dict[str, Any]]) -> 'TradingSettings':
        """Create from structured config dict"""
        # Flatten nested dict
        flat = {}
        for section in config.values():
            flat.update(section)
        
        return cls(**flat)


class TradingSettingsManager:
    """
    Manager for global trading settings
    
    ONE file, ONE set of settings for ALL pairs!
    No more duplication!
    """
    
    def __init__(self, config_file: str = "config/trading_settings.yaml"):
        self.config_file = Path(config_file)
        self.settings: Optional[TradingSettings] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize settings"""
        print("="*70)
        print("📋 TRADING SETTINGS INITIALIZING")
        print("="*70)
        
        if self.config_file.exists():
            print(f"✅ Found settings file: {self.config_file}")
            print("   Loading global settings...")
            self.load()
        else:
            print(f"⚠️  Settings file not found: {self.config_file}")
            print("   Creating default settings...")
            self.create_default()
            self.load()
        
        print(f"✅ Settings loaded:")
        print(f"   Entry: {self.settings.entry_threshold}, Exit: {self.settings.exit_threshold}")
        print(f"   Max Positions: {self.settings.max_positions}, Volume: {self.settings.volume_multiplier}x")
        print(f"   Window: {self.settings.rolling_window_size}, Risk: {self.settings.max_risk_pct}%")
        print("="*70)
        print("")
    
    def load(self):
        """Load settings from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            self.settings = TradingSettings.from_config_dict(config)
            
        except Exception as e:
            print(f"⚠️  Error loading settings: {e}")
            print("   Using defaults...")
            self.settings = TradingSettings()
    
    def save(self):
        """Save settings to file"""
        try:
            # Create directory if needed
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to structured dict
            config = self.settings.to_config_dict()
            
            # Save to YAML
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Settings saved to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
    
    def create_default(self):
        """Create default settings file"""
        self.settings = TradingSettings()
        self.save()
        print(f"✅ Created default settings: {self.config_file}")
    
    def get(self) -> TradingSettings:
        """Get current settings"""
        if self.settings is None:
            self.settings = TradingSettings()
        return self.settings
    
    def update(self, **kwargs):
        """Update settings"""
        if self.settings is None:
            self.settings = TradingSettings()
        
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
    
    def get_dict(self) -> Dict[str, Any]:
        """Get settings as flat dict (for TradingSystem)"""
        return self.settings.to_dict()


class SymbolLoader:
    """
    Load symbol info from MT5 at runtime
    NO file storage - always fresh from broker!
    """
    
    def __init__(self):
        self.cache = {}
    
    def load_pair(self, primary: str, secondary: str) -> Dict[str, Dict[str, Any]]:
        """
        Load symbol pair from MT5
        
        Args:
            primary: Primary symbol (e.g., "XAUUSD")
            secondary: Secondary symbol (e.g., "XAGUSD")
        
        Returns:
            {
                'primary': {'symbol': 'XAUUSD', 'contract_size': 100.0, ...},
                'secondary': {'symbol': 'XAGUSD', 'contract_size': 5000.0, ...}
            }
        
        Raises:
            ValueError: If symbols not found in MT5
        """
        import MetaTrader5 as mt5
        
        # Initialize MT5
        if not mt5.initialize():
            raise ConnectionError("Could not connect to MT5")
        
        # Load primary symbol
        primary_info = mt5.symbol_info(primary)
        if primary_info is None:
            raise ValueError(f"Symbol '{primary}' not found in MT5! Check symbol name.")
        
        # Load secondary symbol
        secondary_info = mt5.symbol_info(secondary)
        if secondary_info is None:
            raise ValueError(f"Symbol '{secondary}' not found in MT5! Check symbol name.")
        
        # Build result
        result = {
            'primary': {
                'symbol': primary,
                'contract_size': primary_info.trade_contract_size,
                'min_lot': primary_info.volume_min,
                'max_lot': primary_info.volume_max,
                'lot_step': primary_info.volume_step,
                'tick_size': primary_info.point,
                'point_value': primary_info.trade_tick_value
            },
            'secondary': {
                'symbol': secondary,
                'contract_size': secondary_info.trade_contract_size,
                'min_lot': secondary_info.volume_min,
                'max_lot': secondary_info.volume_max,
                'lot_step': secondary_info.volume_step,
                'tick_size': secondary_info.point,
                'point_value': secondary_info.trade_tick_value
            }
        }
        
        # Cache for later
        pair_key = f"{primary}_{secondary}"
        self.cache[pair_key] = result
        
        return result
    
    def get_cached(self, primary: str, secondary: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get from cache if exists"""
        pair_key = f"{primary}_{secondary}"
        return self.cache.get(pair_key)
