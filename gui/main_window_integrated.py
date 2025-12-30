"""
Professional Pair Trading GUI - Fully Integrated
Connects GUI to existing trading system without changing logic
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QLineEdit,
    QTextEdit, QSplitter, QFrame, QSpinBox, QDoubleSpinBox,
    QCheckBox, QProgressBar, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette
from datetime import datetime
import json
import logging
import threading

# Import assets (styles only)
from assets import DARCULA_THEME_QSS, apply_theme
from assets.styles import *

# Import configuration system
from config.settings import get_config, ConfigManager, PairConfig

# Import chart widget
from gui.chart_widget import ChartWidget

# Import trading system (EXISTING CODE - NO CHANGES)
# CRITICAL: Use lazy import to avoid triggering main_cli module-level code!
# This prevents TradingSystem from auto-starting when GUI loads
from core.trading_system import TradingSystem

logger = logging.getLogger(__name__)


class StopThread(QThread):
    """Thread to stop trading system without blocking GUI"""
    
    finished_signal = pyqtSignal(bool)  # True if stopped gracefully, False if forced
    log_message = pyqtSignal(str)
    
    def __init__(self, trading_thread):
        super().__init__()
        self.trading_thread = trading_thread
        
    def run(self):
        """Stop trading system in background"""
        try:
            self.log_message.emit("   Stop signal sent to thread...")
            
            # Tell thread to stop
            self.trading_thread.stop()
            
            # Wait for graceful stop (max 10 seconds)
            stopped = self.trading_thread.wait(10000)
            
            if not stopped:
                self.log_message.emit("⚠️  Thread did not stop in 10 seconds, force terminating...")
                self.trading_thread.terminate()
                self.trading_thread.wait(2000)  # Wait for terminate
                self.log_message.emit("   Thread terminated forcefully")
                self.finished_signal.emit(False)  # Forced stop
            else:
                self.log_message.emit("   Thread stopped gracefully")
                self.finished_signal.emit(True)  # Graceful stop
                
        except Exception as e:
            self.log_message.emit(f"❌ Error stopping: {e}")
            self.finished_signal.emit(False)


class TradingSystemThread(QThread):
    """Thread to run trading system without blocking GUI"""
    
    # Signals for GUI updates
    status_update = pyqtSignal(dict)
    position_update = pyqtSignal(list)
    log_message = pyqtSignal(str)
    snapshot_update = pyqtSignal(object)  # ← NEW: For chart updates
    
    def __init__(self, trading_config: dict):
        super().__init__()
        self.trading_config = trading_config
        self.trading_system = None
        self.running = False
        
        # Track statistics
        self.max_zscore = 0.0
        self.min_mean = float('inf')
        self.max_mean = float('-inf')
        
    def run(self):
        """Run trading system in background thread"""
        try:
            # Extract from trading_config FIRST
            symbols = self.trading_config['symbols']
            settings = self.trading_config['settings']
            primary_symbol = self.trading_config['primary_symbol']
            secondary_symbol = self.trading_config['secondary_symbol']
            
            # DEBUG: Log what we received
            self.log_message.emit("")
            self.log_message.emit("🔍 DEBUG - Trading Config Received:")
            self.log_message.emit(f"   Primary Symbol: {primary_symbol}")
            self.log_message.emit(f"   Secondary Symbol: {secondary_symbol}")
            self.log_message.emit(f"   Primary Contract: {symbols['primary']['contract_size']}")
            self.log_message.emit(f"   Secondary Contract: {symbols['secondary']['contract_size']}")
            self.log_message.emit("")
            
            # Get real MT5 balance
            import MetaTrader5 as mt5
            
            # Initialize MT5 if not already
            if not mt5.initialize():
                self.log_message.emit("⚠️  Could not initialize MT5 for balance check")
                real_balance = 100000.0  # Fallback
            else:
                account_info = mt5.account_info()
                if account_info is None:
                    real_balance = 100000.0  # Fallback
                    self.log_message.emit("⚠️  Could not get MT5 balance, using default $100,000")
                else:
                    real_balance = account_info.balance
                    self.log_message.emit(f"✅ MT5 Account Balance: ${real_balance:,.2f}")
                    self.log_message.emit(f"   Account: {account_info.login}")
                    self.log_message.emit(f"   Leverage: 1:{account_info.leverage}")
            
            # Create trading system with symbols + settings!
            self.log_message.emit("")
            self.log_message.emit("🔧 Creating TradingSystem...")
            
            # Add symbols to config dict
            config_with_symbols = settings.copy()
            config_with_symbols['primary_symbol'] = primary_symbol
            config_with_symbols['secondary_symbol'] = secondary_symbol
            
            self.trading_system = TradingSystem(
                account_balance=real_balance,
                config=config_with_symbols  # ← Settings WITH symbols!
            )
            
            # Set symbol info (runtime data)
            self.log_message.emit(f"📝 Setting symbols in market_data:")
            self.log_message.emit(f"   primary_symbol = {primary_symbol}")
            self.log_message.emit(f"   secondary_symbol = {secondary_symbol}")
            self.trading_system.market_data.primary_symbol = primary_symbol
            self.trading_system.market_data.secondary_symbol = secondary_symbol
            self.trading_system.market_data.primary_contract_size = symbols['primary']['contract_size']
            self.trading_system.market_data.secondary_contract_size = symbols['secondary']['contract_size']
            
            # CRITICAL: Also update trade executor symbols!
            self.log_message.emit(f"📝 Setting symbols in trade_executor:")
            self.trading_system.trade_executor.primary_symbol = primary_symbol
            self.trading_system.trade_executor.secondary_symbol = secondary_symbol
            self.log_message.emit(f"   ✅ Executor updated: {primary_symbol}/{secondary_symbol}")
            
            # VERIFY what was actually set
            self.log_message.emit("")
            self.log_message.emit("✅ Verification - Symbols in TradingSystem:")
            self.log_message.emit(f"   market_data.primary_symbol = {self.trading_system.market_data.primary_symbol}")
            self.log_message.emit(f"   market_data.secondary_symbol = {self.trading_system.market_data.secondary_symbol}")
            self.log_message.emit(f"   market_data.primary_contract_size = {self.trading_system.market_data.primary_contract_size}")
            self.log_message.emit(f"   market_data.secondary_contract_size = {self.trading_system.market_data.secondary_contract_size}")
            self.log_message.emit(f"   trade_executor.primary_symbol = {self.trading_system.trade_executor.primary_symbol}")
            self.log_message.emit(f"   trade_executor.secondary_symbol = {self.trading_system.trade_executor.secondary_symbol}")
            self.log_message.emit("")
            
            self.log_message.emit(f"✅ Trading system initialized and ready!")
            self.log_message.emit(f"   Trading Pair: {primary_symbol}/{secondary_symbol}")
            self.log_message.emit(f"   Global config applied")
            
            # Start trading system in separate thread (non-blocking)
            self.running = True
            
            # Start the trading system (this starts its own threads)
            self.trading_system.start()
            
            # Monitor loop - keep thread alive and check running flag
            import time
            while self.running:
                time.sleep(0.5)  # Check every 500ms
                
                # Emit current snapshot for chart updates
                try:
                    if self.trading_system and hasattr(self.trading_system, 'market_data'):
                        snapshot = self.trading_system.market_data.get_realtime_snapshot()
                        if snapshot:
                            self.snapshot_update.emit(snapshot)
                except Exception as e:
                    # Don't crash on snapshot errors
                    pass
                
                # If trading_system stopped itself, exit
                if hasattr(self.trading_system, '_stop_event'):
                    if self.trading_system._stop_event.is_set():
                        self.log_message.emit("⚠️  Trading system stopped itself")
                        break
            
            # Clean exit
            self.log_message.emit("🛑 Trading thread exiting...")
            
        except Exception as e:
            self.log_message.emit(f"❌ Error starting trading system: {str(e)}")
            logger.error(f"Trading system error: {e}", exc_info=True)
        finally:
            # Ensure system is stopped
            if self.trading_system:
                try:
                    self.trading_system.stop()
                except:
                    pass
            self.running = False
    
    def stop(self):
        """Stop trading system"""
        self.running = False
        if self.trading_system:
            # CRITICAL: Must call stop() on TradingSystem to stop its threads!
            self.trading_system.stop()
            self.log_message.emit("⏸️ Trading system stop signal sent")
    
    def get_status(self) -> dict:
        """Get current system status - ALWAYS returns valid dict"""
        
        # Default values (shown when not running)
        default_status = {
            'zscore': 0.0,
            'correlation': 0.0,
            'hedge_ratio': 0.0,
            'spread': 0.0,
            'spread_mean': 0.0,
            'spread_std': 0.0,
            'total_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'open_positions': 0,
            'closed_positions': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'primary_symbol': self.trading_config.get('primary_symbol', 'N/A'),
            'secondary_symbol': self.trading_config.get('secondary_symbol', 'N/A'),
            'signal': 'HOLD'
        }
        
        # If not running, return defaults
        if not self.trading_system or not self.running:
            return default_status
        
        try:
            # Get real data
            snapshot = self.trading_system.market_data.get_realtime_snapshot()
            position_stats = self.trading_system.position_tracker.get_statistics()
            pnl_data = self.trading_system.position_tracker.get_total_pnl()
            
            # Get MT5 risk metrics
            from risk.mt5_risk_monitor import MT5RiskMonitor
            mt5_monitor = MT5RiskMonitor()
            max_risk = self.trading_config['settings'].get('max_risk_pct', 20.0) / 100.0  # Convert to fraction
            
            try:
                mt5_metrics = mt5_monitor.get_metrics(
                    primary_symbol=self.trading_config.get('primary_symbol', 'XAUUSD'),
                    secondary_symbol=self.trading_config.get('secondary_symbol', 'XAGUSD'),
                    target_hedge_ratio=snapshot.hedge_ratio if snapshot else None,
                    max_risk_pct=max_risk
                )
                if not mt5_metrics:
                    logger.warning("MT5RiskMonitor returned None - using defaults")
            except Exception as e:
                logger.error(f"Error getting MT5 metrics: {e}")
                mt5_metrics = None
            
            # Determine signal
            zscore = snapshot.zscore if snapshot else 0.0
            entry = self.trading_config['settings'].get('entry_threshold', 2.0)
            if abs(zscore) >= entry:
                signal = "SHORT SPREAD" if zscore > 0 else "LONG SPREAD"
            else:
                signal = "HOLD"
            
            # Track statistics
            if snapshot:
                # Track max absolute z-score
                if abs(zscore) > abs(self.max_zscore):
                    self.max_zscore = zscore
                
                # Track min/max rolling mean
                current_mean = snapshot.spread_mean
                if current_mean < self.min_mean:
                    self.min_mean = current_mean
                if current_mean > self.max_mean:
                    self.max_mean = current_mean
            
            return {
                'zscore': zscore,
                'correlation': snapshot.correlation if snapshot else 0.0,
                'hedge_ratio': snapshot.hedge_ratio if snapshot else 0.0,
                'spread': snapshot.spread if snapshot else 0.0,
                'spread_mean': snapshot.spread_mean if snapshot else 0.0,
                'spread_std': snapshot.spread_std if snapshot else 0.0,
                'total_pnl': pnl_data.get('total_pnl', 0.0),
                'unrealized_pnl': pnl_data.get('unrealized_pnl', 0.0),
                'realized_pnl': pnl_data.get('realized_pnl', 0.0),
                'open_positions': pnl_data.get('open_positions', 0),
                'closed_positions': pnl_data.get('closed_positions', 0),
                'win_rate': position_stats.get('win_rate', 0.0) if position_stats else 0.0,
                'avg_profit': position_stats.get('avg_profit', 0.0) if position_stats else 0.0,
                'primary_symbol': self.trading_config.get('primary_symbol', 'N/A'),
                'secondary_symbol': self.trading_config.get('secondary_symbol', 'N/A'),
                'signal': signal,
                # New statistics
                'max_zscore': self.max_zscore,
                'min_mean': self.min_mean if self.min_mean != float('inf') else 0.0,
                'max_mean': self.max_mean if self.max_mean != float('-inf') else 0.0,
                # MT5 Risk Metrics
                'mt5_balance': mt5_metrics.balance if mt5_metrics else 0.0,
                'mt5_equity': mt5_metrics.equity if mt5_metrics else 0.0,
                'mt5_margin': mt5_metrics.margin if mt5_metrics else 0.0,
                'mt5_margin_free': mt5_metrics.margin_free if mt5_metrics else 0.0,
                'mt5_margin_level': mt5_metrics.margin_level if mt5_metrics else 0.0,
                'mt5_profit': mt5_metrics.profit if mt5_metrics else 0.0,
                'mt5_positions': mt5_metrics.total_positions if mt5_metrics else 0,
                'mt5_primary_lots': mt5_metrics.primary_lots if mt5_metrics else 0.0,
                'mt5_secondary_lots': mt5_metrics.secondary_lots if mt5_metrics else 0.0,
                'mt5_hedge_imbalance': mt5_metrics.hedge_imbalance if mt5_metrics else 0.0,
                'mt5_hedge_imbalance_pct': mt5_metrics.hedge_imbalance_pct if mt5_metrics else 0.0,
                'mt5_hedge_imbalance_value': mt5_metrics.hedge_imbalance_value if mt5_metrics else 0.0,
                'mt5_max_risk_pct': mt5_metrics.max_risk_pct * 100 if mt5_metrics else 20.0,  # As percentage
                'mt5_stop_loss_level': mt5_metrics.stop_loss_level if mt5_metrics else 0.0,
                'mt5_risk_amount': mt5_metrics.risk_amount if mt5_metrics else 0.0,
                'mt5_distance_to_sl_pct': mt5_metrics.distance_to_sl_pct if mt5_metrics else 0.0
            }
        
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            return default_status  # Return defaults on error
    
    def get_positions(self) -> list:
        """Get current positions"""
        if not self.trading_system:
            return []
        
        try:
            positions = []
            for pos in self.trading_system.position_tracker.get_all_positions():
                # Use spread_id from metadata (ticket-based) instead of position_id (UUID)
                spread_id = pos.metadata.get('spread_id', pos.position_id)
                
                # Format spread_id for display
                if '-' in spread_id:
                    # Ticket-based format: "1538873231-1538873233"
                    # Show as: "8231-3233" (last 4 digits of each ticket)
                    parts = spread_id.split('-')
                    if len(parts) == 2:
                        display_id = f"{parts[0][-4:]}-{parts[1][-4:]}"
                    else:
                        display_id = spread_id[:8]
                else:
                    # UUID format or other
                    display_id = spread_id[:8]
                
                positions.append({
                    'id': display_id,  # Display shortened spread_id
                    'symbol': pos.symbol,
                    'side': pos.side,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'opened_at': pos.opened_at.strftime("%H:%M:%S"),
                    'metadata': pos.metadata
                })
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []


class PairTradingGUI(QMainWindow):
    """Main GUI Window - Integrated with Trading System"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pair Trading System - Professional Edition")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Apply PyCharm Darcula theme from assets
        self.setStyleSheet(DARCULA_THEME_QSS)
        
        # Initialize state
        self.trading_thread = None
        
        # NEW: Use simplified settings manager (one global config!)
        from config.trading_settings import TradingSettingsManager, SymbolLoader
        self.settings_manager = TradingSettingsManager()
        self.symbol_loader = SymbolLoader()
        
        self.current_pair = None
        
        # Create UI
        self.init_ui()
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
        
        # Load settings into GUI
        self.load_settings_into_gui()
        
        # Initial startup message
        self.add_log("="*70)
        self.add_log("PAIR TRADING SYSTEM - PROFESSIONAL EDITION")
        self.add_log("="*70)
        self.add_log("")
        self.add_log("✅ GUI initialized successfully")
        self.add_log(f"📂 Settings loaded from: config/trading_settings.yaml")
        self.add_log(f"⚙️  Global settings apply to ALL pairs")
        self.add_log("")
        self.add_log("📋 READY TO START:")
        self.add_log("   1. Enter symbols (or use defaults)")
        self.add_log("   2. Adjust settings if needed")
        self.add_log("   3. Click 'Start Trading'")
        self.add_log("   4. System will auto-save config on start")
        self.add_log("")
        self.add_log("💡 System will NOT auto-start - waiting for your command!")
        self.add_log("="*70)
        
    def init_ui(self):
        """Initialize the user interface"""
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 10))
        
        # Add tabs
        self.dashboard_tab = self.create_dashboard_tab()
        self.chart_tab = self.create_chart_tab()  # ← NEW: Chart tab
        self.settings_tab = self.create_settings_tab()
        self.logs_tab = self.create_logs_tab()
        
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.chart_tab, "📈 Charts")  # ← NEW: Charts tab
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        self.tabs.addTab(self.logs_tab, "📝 Logs")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Select pair and start trading")
        
    def load_settings_into_gui(self):
        """
        Load global settings into GUI controls
        ONE set of settings applies to ALL pairs!
        """
        settings = self.settings_manager.get()
        
        # Trading parameters
        self.entry_zscore_spin.setValue(settings.entry_threshold)
        self.exit_zscore_spin.setValue(settings.exit_threshold)
        self.stop_zscore_spin.setValue(settings.stop_loss_zscore)
        self.max_positions_spin.setValue(settings.max_positions)
        self.volume_mult_spin.setValue(settings.volume_multiplier)
        
        # Model parameters
        self.window_spin.setValue(settings.rolling_window_size)
        self.interval_spin.setValue(settings.update_interval)
        self.hedge_drift_spin.setValue(settings.hedge_drift_threshold)
        
        # Risk parameters
        self.max_pos_pct_spin.setValue(settings.max_position_pct)
        self.max_risk_pct_spin.setValue(settings.max_risk_pct)
        self.daily_loss_spin.setValue(settings.daily_loss_limit)
        
        # Feature flags
        self.pyramiding_check.setChecked(settings.enable_pyramiding)
        self.hedge_adjust_check.setChecked(settings.enable_hedge_adjustment)
        
        # Advanced settings
        self.scale_interval_spin.setValue(settings.scale_interval)
        self.initial_fraction_spin.setValue(settings.initial_fraction)
        self.min_adjust_interval_spin.setValue(settings.min_adjustment_interval)
        self.magic_number_spin.setValue(settings.magic_number)
        self.zscore_history_spin.setValue(settings.zscore_history_size)
        
        # Update displays
        self.entry_threshold_display.setText(f"{settings.entry_threshold:.1f}")
        self.exit_threshold_display.setText(f"{settings.exit_threshold:.1f}")
        self.window_size_display.setText(f"{settings.rolling_window_size}")
        
        # Set default symbols
        self.primary_input.setText("XAUUSD")
        self.secondary_input.setText("XAGUSD")
    
    def populate_symbols(self):
        """
        DEPRECATED - Kept for compatibility
        Old method that loaded from pairs config
        Now we use load_settings_into_gui() instead
        """
        pass
    
    def update_dashboard_from_config(self, pair: PairConfig):
        """Update dashboard display labels from config"""
        # Update Model Metrics display on Dashboard
        self.entry_threshold_display.setText(f"{pair.entry_threshold:.1f}")
        self.exit_threshold_display.setText(f"{pair.exit_threshold:.1f}")
        self.window_size_display.setText(f"{pair.rolling_window_size}")
        
        # Update status
        self.statusBar.showMessage(f"Configuration loaded: {pair.primary_symbol}/{pair.secondary_symbol}")
    
    def create_dashboard_tab(self):
        """Create main dashboard tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ========== Top Control Panel ==========
        control_panel = QGroupBox("Control Panel")
        control_layout = QHBoxLayout()
        
        # Symbol selection
        symbol_group = QGroupBox("Symbol Selection")
        symbol_layout = QGridLayout()
        
        # Primary symbol input (text field instead of dropdown!)
        symbol_layout.addWidget(QLabel("Primary Symbol:"), 0, 0)
        self.primary_input = QLineEdit()
        self.primary_input.setPlaceholderText("e.g., XAUUSD, GOLD, XAU/USD...")
        self.primary_input.setMinimumWidth(150)
        self.primary_input.setText("XAUUSD")  # Default
        self.primary_input.textChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.primary_input, 0, 1)
        
        # Secondary symbol input (text field instead of dropdown!)
        symbol_layout.addWidget(QLabel("Secondary Symbol:"), 1, 0)
        self.secondary_input = QLineEdit()
        self.secondary_input.setPlaceholderText("e.g., XAGUSD, SILVER, XAG/USD...")
        self.secondary_input.setMinimumWidth(150)
        self.secondary_input.setText("XAGUSD")  # Default
        self.secondary_input.textChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.secondary_input, 1, 1)
        
        # Analyze button removed - not needed yet
        # self.analyze_btn = QPushButton("🔍 Analyze Pair")
        # self.analyze_btn.clicked.connect(self.analyze_pair)
        # symbol_layout.addWidget(self.analyze_btn, 0, 2)
        
        self.start_stop_btn = QPushButton("▶️ Start Trading")
        self.start_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.start_stop_btn.clicked.connect(self.toggle_trading)
        symbol_layout.addWidget(self.start_stop_btn, 1, 2)
        
        symbol_group.setLayout(symbol_layout)
        control_layout.addWidget(symbol_group)
        
        # Live statistics
        stats_group = QGroupBox("Live Statistics")
        stats_layout = QGridLayout()
        
        self.zscore_label = QLabel("--")
        self.zscore_label.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        stats_layout.addWidget(QLabel("Z-Score:"), 0, 0)
        stats_layout.addWidget(self.zscore_label, 0, 1)
        
        self.correlation_label = QLabel("--")
        stats_layout.addWidget(QLabel("Correlation:"), 1, 0)
        stats_layout.addWidget(self.correlation_label, 1, 1)
        
        self.hedge_ratio_label = QLabel("--")
        stats_layout.addWidget(QLabel("Hedge Ratio:"), 2, 0)
        stats_layout.addWidget(self.hedge_ratio_label, 2, 1)
        
        self.spread_label = QLabel("--")
        stats_layout.addWidget(QLabel("Spread:"), 0, 2)
        stats_layout.addWidget(self.spread_label, 0, 3)
        
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        stats_layout.addWidget(QLabel("Total P&L:"), 1, 2)
        stats_layout.addWidget(self.pnl_label, 1, 3)
        
        self.signal_label = QLabel("HOLD")
        self.signal_label.setStyleSheet("background-color: #7f8c8d; color: white; padding: 5px; border-radius: 3px; font-weight: bold;")
        stats_layout.addWidget(QLabel("Signal:"), 2, 2)
        stats_layout.addWidget(self.signal_label, 2, 3)
        
        stats_group.setLayout(stats_layout)
        control_layout.addWidget(stats_group)
        
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        
        # ========== Model Metrics Panel ==========
        metrics_panel = QGroupBox("Model Metrics")
        metrics_layout = QGridLayout()
        
        metrics_layout.addWidget(QLabel("Entry Threshold:"), 0, 0)
        self.entry_threshold_display = QLabel("2.0")
        self.entry_threshold_display.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.entry_threshold_display, 0, 1)
        
        metrics_layout.addWidget(QLabel("Exit Threshold:"), 0, 2)
        self.exit_threshold_display = QLabel("0.5")
        self.exit_threshold_display.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.exit_threshold_display, 0, 3)
        
        metrics_layout.addWidget(QLabel("Window Size:"), 0, 4)
        self.window_size_display = QLabel("200")
        self.window_size_display.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.window_size_display, 0, 5)
        
        metrics_layout.addWidget(QLabel("Spread Mean:"), 1, 0)
        self.mean_label = QLabel("--")
        metrics_layout.addWidget(self.mean_label, 1, 1)
        
        metrics_layout.addWidget(QLabel("Spread Std:"), 1, 2)
        self.std_label = QLabel("--")
        metrics_layout.addWidget(self.std_label, 1, 3)
        
        metrics_layout.addWidget(QLabel("Open/Closed:"), 1, 4)
        self.positions_count_label = QLabel("0 / 0")
        metrics_layout.addWidget(self.positions_count_label, 1, 5)
        
        # ========== Row 2: Statistics (Max Z-Score, Min/Max Mean) ==========
        metrics_layout.addWidget(QLabel("Max Z-Score:"), 2, 0)
        self.max_zscore_label = QLabel("--")
        self.max_zscore_label.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.max_zscore_label, 2, 1)
        
        metrics_layout.addWidget(QLabel("Min Mean:"), 2, 2)
        self.min_mean_label = QLabel("--")
        self.min_mean_label.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.min_mean_label, 2, 3)
        
        metrics_layout.addWidget(QLabel("Max Mean:"), 2, 4)
        self.max_mean_label = QLabel("--")
        self.max_mean_label.setFont(QFont("Courier New", 10))
        metrics_layout.addWidget(self.max_mean_label, 2, 5)
        
        # ========== Row 3: Last Update & Status (bottom) ==========
        metrics_layout.addWidget(QLabel("Last Update:"), 3, 0)
        self.last_update_label = QLabel("--")
        metrics_layout.addWidget(self.last_update_label, 3, 1, 1, 2)
        
        metrics_layout.addWidget(QLabel("Status:"), 3, 3)
        self.status_indicator = QLabel("⚫ Stopped")
        self.status_indicator.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        metrics_layout.addWidget(self.status_indicator, 3, 4, 1, 2)
        
        metrics_panel.setLayout(metrics_layout)
        layout.addWidget(metrics_panel)
        
        # ========== MT5 Risk Management Panel ==========
        mt5_risk_panel = QGroupBox("🔒 MT5 Risk Management (Real-Time)")
        mt5_risk_layout = QGridLayout()
        
        # Row 0: Balance & Equity
        mt5_risk_layout.addWidget(QLabel("MT5 Balance:"), 0, 0)
        self.mt5_balance_label = QLabel("--")  # Start with visible placeholder
        self.mt5_balance_label.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        self.mt5_balance_label.setStyleSheet("color: #FFFFFF; background-color: #34495e; padding: 2px;")  # White text, dark bg
        mt5_risk_layout.addWidget(self.mt5_balance_label, 0, 1)
        
        mt5_risk_layout.addWidget(QLabel("MT5 Equity:"), 0, 2)
        self.mt5_equity_label = QLabel("$0.00")
        self.mt5_equity_label.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        self.mt5_equity_label.setStyleSheet("color: #27ae60;")
        mt5_risk_layout.addWidget(self.mt5_equity_label, 0, 3)
        
        mt5_risk_layout.addWidget(QLabel("Unrealized P&L:"), 0, 4)
        self.mt5_profit_label = QLabel("$0.00")
        self.mt5_profit_label.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        mt5_risk_layout.addWidget(self.mt5_profit_label, 0, 5)
        
        # Row 1: Margin Info
        mt5_risk_layout.addWidget(QLabel("Used Margin:"), 1, 0)
        self.mt5_margin_label = QLabel("$0.00")
        mt5_risk_layout.addWidget(self.mt5_margin_label, 1, 1)
        
        mt5_risk_layout.addWidget(QLabel("Free Margin:"), 1, 2)
        self.mt5_margin_free_label = QLabel("$0.00")
        mt5_risk_layout.addWidget(self.mt5_margin_free_label, 1, 3)
        
        mt5_risk_layout.addWidget(QLabel("Margin Level:"), 1, 4)
        self.mt5_margin_level_label = QLabel("0.0%")
        self.mt5_margin_level_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        mt5_risk_layout.addWidget(self.mt5_margin_level_label, 1, 5)
        
        # Row 2: Position Lots
        mt5_risk_layout.addWidget(QLabel("Primary Lots:"), 2, 0)
        self.mt5_primary_lots_label = QLabel("0.00")
        self.mt5_primary_lots_label.setFont(QFont("Courier New", 10))
        mt5_risk_layout.addWidget(self.mt5_primary_lots_label, 2, 1)
        
        mt5_risk_layout.addWidget(QLabel("Secondary Lots:"), 2, 2)
        self.mt5_secondary_lots_label = QLabel("0.00")
        self.mt5_secondary_lots_label.setFont(QFont("Courier New", 10))
        mt5_risk_layout.addWidget(self.mt5_secondary_lots_label, 2, 3)
        
        mt5_risk_layout.addWidget(QLabel("MT5 Positions:"), 2, 4)
        self.mt5_positions_label = QLabel("0")
        mt5_risk_layout.addWidget(self.mt5_positions_label, 2, 5)
        
        # Row 3: Hedge Imbalance (CRITICAL!)
        mt5_risk_layout.addWidget(QLabel("Hedge Imbalance:"), 3, 0)
        self.mt5_hedge_imbalance_label = QLabel("0.0000 lots")
        self.mt5_hedge_imbalance_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.mt5_hedge_imbalance_label.setStyleSheet("color: #e67e22;")
        mt5_risk_layout.addWidget(self.mt5_hedge_imbalance_label, 3, 1)
        
        mt5_risk_layout.addWidget(QLabel("Imbalance %:"), 3, 2)
        self.mt5_hedge_imbalance_pct_label = QLabel("0.00%")
        self.mt5_hedge_imbalance_pct_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        mt5_risk_layout.addWidget(self.mt5_hedge_imbalance_pct_label, 3, 3)
        
        mt5_risk_layout.addWidget(QLabel("Value:"), 3, 4)
        self.mt5_hedge_imbalance_value_label = QLabel("$0.00")
        self.mt5_hedge_imbalance_value_label.setFont(QFont("Courier New", 10))
        mt5_risk_layout.addWidget(self.mt5_hedge_imbalance_value_label, 3, 5)
        
        # Row 4: Stop Loss & Risk
        mt5_risk_layout.addWidget(QLabel("Stop Loss Level:"), 4, 0)
        self.mt5_stop_loss_label = QLabel("$0.00")
        self.mt5_stop_loss_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.mt5_stop_loss_label.setStyleSheet("color: #e74c3c;")
        mt5_risk_layout.addWidget(self.mt5_stop_loss_label, 4, 1)
        
        mt5_risk_layout.addWidget(QLabel("Max Risk:"), 4, 2)
        self.mt5_max_risk_label = QLabel("20.0%")
        self.mt5_max_risk_label.setFont(QFont("Courier New", 10))
        mt5_risk_layout.addWidget(self.mt5_max_risk_label, 4, 3)
        
        mt5_risk_layout.addWidget(QLabel("Risk Amount:"), 4, 4)
        self.mt5_risk_amount_label = QLabel("$0.00")
        self.mt5_risk_amount_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.mt5_risk_amount_label.setStyleSheet("color: #e74c3c;")
        mt5_risk_layout.addWidget(self.mt5_risk_amount_label, 4, 5)
        
        mt5_risk_layout.addWidget(QLabel("Distance:"), 4, 6)
        self.mt5_distance_to_sl_label = QLabel("0.0%")
        self.mt5_distance_to_sl_label.setFont(QFont("Courier New", 10))
        mt5_risk_layout.addWidget(self.mt5_distance_to_sl_label, 4, 7)
        
        mt5_risk_panel.setLayout(mt5_risk_layout)
        layout.addWidget(mt5_risk_panel)
        
        # ========== P&L Attribution Panel ==========
        attribution_panel = QGroupBox("📊 P&L Attribution (Real-Time)")
        attribution_layout = QGridLayout()
        
        # Row 0: Spread P&L
        attribution_layout.addWidget(QLabel("Spread P&L:"), 0, 0)
        self.attr_spread_pnl_label = QLabel("$0.00")
        self.attr_spread_pnl_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.attr_spread_pnl_label.setStyleSheet("color: #3498db;")
        attribution_layout.addWidget(self.attr_spread_pnl_label, 0, 1)
        
        self.attr_spread_pct_label = QLabel("0.0%")
        self.attr_spread_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_spread_pct_label, 0, 2)
        
        # Row 1: Mean Drift P&L
        attribution_layout.addWidget(QLabel("Mean Drift P&L:"), 1, 0)
        self.attr_mean_pnl_label = QLabel("$0.00")
        self.attr_mean_pnl_label.setFont(QFont("Courier New", 10))
        self.attr_mean_pnl_label.setStyleSheet("color: #9b59b6;")
        attribution_layout.addWidget(self.attr_mean_pnl_label, 1, 1)
        
        self.attr_mean_pct_label = QLabel("0.0%")
        self.attr_mean_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_mean_pct_label, 1, 2)
        
        # Row 2: Directional P&L
        attribution_layout.addWidget(QLabel("Directional P&L:"), 2, 0)
        self.attr_directional_pnl_label = QLabel("$0.00")
        self.attr_directional_pnl_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.attr_directional_pnl_label.setStyleSheet("color: #95a5a6;")
        attribution_layout.addWidget(self.attr_directional_pnl_label, 2, 1)
        
        self.attr_directional_pct_label = QLabel("0.0%")
        self.attr_directional_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_directional_pct_label, 2, 2)
        
        # Row 3: Hedge Imbalance P&L
        attribution_layout.addWidget(QLabel("Hedge Imbalance:"), 3, 0)
        self.attr_hedge_pnl_label = QLabel("$0.00")
        self.attr_hedge_pnl_label.setFont(QFont("Courier New", 10))
        attribution_layout.addWidget(self.attr_hedge_pnl_label, 3, 1)
        
        self.attr_hedge_pct_label = QLabel("0.0%")
        self.attr_hedge_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_hedge_pct_label, 3, 2)
        
        # Spacer column
        attribution_layout.setColumnMinimumWidth(3, 30)
        
        # Row 0 (right side): Transaction Costs
        attribution_layout.addWidget(QLabel("Transaction Costs:"), 0, 4)
        self.attr_costs_label = QLabel("$0.00")
        self.attr_costs_label.setFont(QFont("Courier New", 10))
        self.attr_costs_label.setStyleSheet("color: #e74c3c;")
        attribution_layout.addWidget(self.attr_costs_label, 0, 5)
        
        self.attr_costs_pct_label = QLabel("0.0%")
        self.attr_costs_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_costs_pct_label, 0, 6)
        
        # Row 1 (right side): Slippage
        attribution_layout.addWidget(QLabel("Slippage:"), 1, 4)
        self.attr_slippage_label = QLabel("$0.00")
        self.attr_slippage_label.setFont(QFont("Courier New", 10))
        attribution_layout.addWidget(self.attr_slippage_label, 1, 5)
        
        self.attr_slippage_pct_label = QLabel("0.0%")
        self.attr_slippage_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_slippage_pct_label, 1, 6)
        
        # Row 2 (right side): Rebalance Alpha
        attribution_layout.addWidget(QLabel("Rebalance Alpha:"), 2, 4)
        self.attr_rebalance_label = QLabel("$0.00")
        self.attr_rebalance_label.setFont(QFont("Courier New", 10))
        self.attr_rebalance_label.setStyleSheet("color: #27ae60;")
        attribution_layout.addWidget(self.attr_rebalance_label, 2, 5)
        
        self.attr_rebalance_pct_label = QLabel("0.0%")
        self.attr_rebalance_pct_label.setFont(QFont("Courier New", 9))
        attribution_layout.addWidget(self.attr_rebalance_pct_label, 2, 6)
        
        # Separator line
        separator = QLabel("─" * 80)
        separator.setStyleSheet("color: #34495e;")
        attribution_layout.addWidget(separator, 4, 0, 1, 7)
        
        # Row 5: Quality Metrics
        attribution_layout.addWidget(QLabel("Hedge Quality:"), 5, 0)
        self.attr_hedge_quality_label = QLabel("--")
        self.attr_hedge_quality_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.attr_hedge_quality_label.setStyleSheet("color: #95a5a6;")
        attribution_layout.addWidget(self.attr_hedge_quality_label, 5, 1)
        
        attribution_layout.addWidget(QLabel("Strategy Purity:"), 5, 2)
        self.attr_purity_label = QLabel("--")
        self.attr_purity_label.setFont(QFont("Courier New", 10))
        attribution_layout.addWidget(self.attr_purity_label, 5, 3)
        
        attribution_layout.addWidget(QLabel("Classification:"), 5, 4)
        self.attr_class_label = QLabel("NO DATA")
        self.attr_class_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.attr_class_label.setStyleSheet("color: #95a5a6;")
        attribution_layout.addWidget(self.attr_class_label, 5, 5, 1, 2)
        
        attribution_panel.setLayout(attribution_layout)
        layout.addWidget(attribution_panel)
        
        # ========== Positions Table ==========
        positions_group = QGroupBox("Open Positions")
        positions_layout = QVBoxLayout()
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(10)
        self.positions_table.setHorizontalHeaderLabels([
            "ID", "Symbol", "Side", "Quantity",  
            "Entry Price", "Current Price", "P&L", 
            "Entry Time", "Entry Z", "Status"
        ])
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.horizontalHeader().setStretchLastSection(True)
        self.positions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        positions_layout.addWidget(self.positions_table)
        positions_group.setLayout(positions_layout)
        layout.addWidget(positions_group)
        
        return tab
    
    def create_chart_tab(self):
        """Create real-time chart tab"""
        self.chart_widget = ChartWidget()
        return self.chart_widget
    
    def create_settings_tab(self):
        """Create settings configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Split into sections
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ========== Trading Parameters ==========
        trading_group = QGroupBox("Trading Parameters")
        trading_layout = QGridLayout()
        
        row = 0
        trading_layout.addWidget(QLabel("Entry Z-Score:"), row, 0)
        self.entry_zscore_spin = QDoubleSpinBox()
        self.entry_zscore_spin.setRange(0.1, 5.0)
        self.entry_zscore_spin.setValue(2.0)
        self.entry_zscore_spin.setSingleStep(0.1)
        trading_layout.addWidget(self.entry_zscore_spin, row, 1)
        
        row += 1
        trading_layout.addWidget(QLabel("Exit Z-Score:"), row, 0)
        self.exit_zscore_spin = QDoubleSpinBox()
        self.exit_zscore_spin.setRange(0.0, 2.0)
        self.exit_zscore_spin.setValue(0.5)
        self.exit_zscore_spin.setSingleStep(0.1)
        trading_layout.addWidget(self.exit_zscore_spin, row, 1)
        
        row += 1
        trading_layout.addWidget(QLabel("Stop Loss Z-Score:"), row, 0)
        self.stop_zscore_spin = QDoubleSpinBox()
        self.stop_zscore_spin.setRange(2.0, 10.0)
        self.stop_zscore_spin.setValue(3.5)
        self.stop_zscore_spin.setSingleStep(0.5)
        trading_layout.addWidget(self.stop_zscore_spin, row, 1)
        
        row += 1
        trading_layout.addWidget(QLabel("Max Positions:"), row, 0)
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 20)
        self.max_positions_spin.setValue(10)
        trading_layout.addWidget(self.max_positions_spin, row, 1)
        
        row += 1
        trading_layout.addWidget(QLabel("Volume Multiplier:"), row, 0)
        self.volume_mult_spin = QDoubleSpinBox()
        self.volume_mult_spin.setRange(0.01, 100.0)
        self.volume_mult_spin.setValue(1.0)
        self.volume_mult_spin.setSingleStep(0.1)
        trading_layout.addWidget(self.volume_mult_spin, row, 1)
        
        trading_group.setLayout(trading_layout)
        splitter.addWidget(trading_group)
        
        # ========== Model Parameters ==========
        model_group = QGroupBox("Model Parameters")
        model_layout = QGridLayout()
        
        row = 0
        model_layout.addWidget(QLabel("Rolling Window:"), row, 0)
        self.window_spin = QSpinBox()
        self.window_spin.setRange(50, 1000)
        self.window_spin.setValue(200)
        self.window_spin.setSingleStep(10)
        model_layout.addWidget(self.window_spin, row, 1)
        
        row += 1
        model_layout.addWidget(QLabel("Update Interval (s):"), row, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 300)
        self.interval_spin.setValue(60)
        model_layout.addWidget(self.interval_spin, row, 1)
        
        row += 1
        model_layout.addWidget(QLabel("Hedge Drift Threshold:"), row, 0)
        self.hedge_drift_spin = QDoubleSpinBox()
        self.hedge_drift_spin.setRange(0.01, 0.5)
        self.hedge_drift_spin.setValue(0.05)
        self.hedge_drift_spin.setSingleStep(0.01)
        model_layout.addWidget(self.hedge_drift_spin, row, 1)
        
        row += 1
        self.pyramiding_check = QCheckBox("Enable Pyramiding")
        self.pyramiding_check.setChecked(True)
        model_layout.addWidget(self.pyramiding_check, row, 0, 1, 2)
        
        row += 1
        self.hedge_adjust_check = QCheckBox("Enable Hedge Adjustment")
        self.hedge_adjust_check.setChecked(True)
        model_layout.addWidget(self.hedge_adjust_check, row, 0, 1, 2)
        
        model_group.setLayout(model_layout)
        splitter.addWidget(model_group)
        
        # ========== Risk Management ==========
        risk_group = QGroupBox("Risk Management")
        risk_layout = QGridLayout()
        
        row = 0
        risk_layout.addWidget(QLabel("Max Position %:"), row, 0)
        self.max_pos_pct_spin = QDoubleSpinBox()
        self.max_pos_pct_spin.setRange(1.0, 50.0)
        self.max_pos_pct_spin.setValue(20.0)
        self.max_pos_pct_spin.setSuffix("%")
        risk_layout.addWidget(self.max_pos_pct_spin, row, 1)
        
        row += 1
        risk_layout.addWidget(QLabel("Max Risk %:"), row, 0)
        self.max_risk_pct_spin = QDoubleSpinBox()
        self.max_risk_pct_spin.setRange(0.5, 10.0)
        self.max_risk_pct_spin.setValue(2.0)
        self.max_risk_pct_spin.setSuffix("%")
        risk_layout.addWidget(self.max_risk_pct_spin, row, 1)
        
        row += 1
        risk_layout.addWidget(QLabel("Daily Loss Limit:"), row, 0)
        self.daily_loss_spin = QDoubleSpinBox()
        self.daily_loss_spin.setRange(100, 50000)
        self.daily_loss_spin.setValue(5000)
        self.daily_loss_spin.setPrefix("$")
        risk_layout.addWidget(self.daily_loss_spin, row, 1)
        
        risk_group.setLayout(risk_layout)
        splitter.addWidget(risk_group)
        
        # Advanced Settings (Rebalancer & System Parameters)
        advanced_group = QGroupBox("⚙️ Advanced Settings")
        advanced_layout = QGridLayout()
        row = 0
        
        # Pyramiding settings
        advanced_layout.addWidget(QLabel("Scale Interval (Z-score):"), row, 0)
        self.scale_interval_spin = QDoubleSpinBox()
        self.scale_interval_spin.setRange(0.1, 2.0)
        self.scale_interval_spin.setSingleStep(0.1)
        self.scale_interval_spin.setValue(0.5)
        self.scale_interval_spin.setDecimals(1)
        self.scale_interval_spin.setToolTip("Pyramiding every N z-score units")
        advanced_layout.addWidget(self.scale_interval_spin, row, 1)
        row += 1
        
        advanced_layout.addWidget(QLabel("Initial Position Fraction:"), row, 0)
        self.initial_fraction_spin = QDoubleSpinBox()
        self.initial_fraction_spin.setRange(0.1, 1.0)
        self.initial_fraction_spin.setSingleStep(0.05)
        self.initial_fraction_spin.setValue(0.33)
        self.initial_fraction_spin.setDecimals(2)
        self.initial_fraction_spin.setToolTip("First entry uses this fraction of total position (0.33 = 33%)")
        advanced_layout.addWidget(self.initial_fraction_spin, row, 1)
        row += 1
        
        advanced_layout.addWidget(QLabel("Min Adjustment Interval (sec):"), row, 0)
        self.min_adjust_interval_spin = QSpinBox()
        self.min_adjust_interval_spin.setRange(300, 14400)  # 5 min to 4 hours
        self.min_adjust_interval_spin.setSingleStep(300)
        self.min_adjust_interval_spin.setValue(3600)  # 1 hour
        self.min_adjust_interval_spin.setToolTip("Minimum time between hedge adjustments")
        advanced_layout.addWidget(self.min_adjust_interval_spin, row, 1)
        row += 1
        
        # System settings
        advanced_layout.addWidget(QLabel("Magic Number:"), row, 0)
        self.magic_number_spin = QSpinBox()
        self.magic_number_spin.setRange(100000, 999999)
        self.magic_number_spin.setSingleStep(1)
        self.magic_number_spin.setValue(234000)
        self.magic_number_spin.setToolTip("MT5 Magic Number for trade identification")
        advanced_layout.addWidget(self.magic_number_spin, row, 1)
        row += 1
        
        advanced_layout.addWidget(QLabel("Z-Score History Size:"), row, 0)
        self.zscore_history_spin = QSpinBox()
        self.zscore_history_spin.setRange(50, 1000)
        self.zscore_history_spin.setSingleStep(50)
        self.zscore_history_spin.setValue(200)
        self.zscore_history_spin.setToolTip("Number of z-score values to keep in history")
        advanced_layout.addWidget(self.zscore_history_spin, row, 1)
        row += 1
        
        advanced_group.setLayout(advanced_layout)
        splitter.addWidget(advanced_group)
        
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        apply_btn = QPushButton("✅ Apply to Current Pair")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return tab
    
    def create_logs_tab(self):
        """Create logs viewing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Log controls
        controls = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        controls.addWidget(clear_btn)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_display)
        
        return tab
    
    def on_symbol_changed(self):
        """
        Handle symbol input change
        With simplified config, we just show what symbols are entered
        Settings are global, not per-pair!
        """
        primary = self.primary_input.text().strip()
        secondary = self.secondary_input.text().strip()
        
        if primary and secondary and primary != secondary:
            self.statusBar.showMessage(f"Ready to trade: {primary}/{secondary}")
            self.add_log(f"📊 Symbols: {primary} / {secondary}")
            self.add_log(f"   Global settings will be applied")
        elif primary == secondary:
            self.statusBar.showMessage("Error: Primary and secondary must be different")
        else:
            self.statusBar.showMessage("Enter both symbols to begin")
    
    def load_pair_settings(self, pair: PairConfig):
        """Load pair configuration into GUI"""
        self.current_pair = pair
        
        # Update displays
        self.entry_threshold_display.setText(f"{pair.entry_threshold:.1f}")
        self.exit_threshold_display.setText(f"{pair.exit_threshold:.1f}")
        self.window_size_display.setText(f"{pair.rolling_window_size}")
        
        # Update spinboxes
        self.entry_zscore_spin.setValue(pair.entry_threshold)
        self.exit_zscore_spin.setValue(pair.exit_threshold)
        self.stop_zscore_spin.setValue(pair.stop_loss_zscore)
        self.max_positions_spin.setValue(pair.max_positions)
        self.volume_mult_spin.setValue(pair.volume_multiplier)
        
        self.window_spin.setValue(pair.rolling_window_size)
        self.interval_spin.setValue(pair.update_interval)
        self.hedge_drift_spin.setValue(pair.hedge_drift_threshold)
        
        self.pyramiding_check.setChecked(pair.enable_pyramiding)
        self.hedge_adjust_check.setChecked(pair.enable_hedge_adjustment)
        
        self.max_pos_pct_spin.setValue(pair.max_position_pct)
        self.max_risk_pct_spin.setValue(pair.max_risk_pct)
        self.daily_loss_spin.setValue(pair.daily_loss_limit)
        
        # Load advanced settings (with defaults if not present)
        self.scale_interval_spin.setValue(getattr(pair, 'scale_interval', 0.5))
        self.initial_fraction_spin.setValue(getattr(pair, 'initial_fraction', 0.33))
        self.min_adjust_interval_spin.setValue(getattr(pair, 'min_adjustment_interval', 3600))
        self.magic_number_spin.setValue(getattr(pair, 'magic_number', 234000))
        self.zscore_history_spin.setValue(getattr(pair, 'zscore_history_size', 200))
    
    def analyze_pair(self):
        """Analyze selected pair for cointegration"""
        primary = self.primary_input.text().strip()
        secondary = self.secondary_input.text().strip()
        
        if not primary or not secondary:
            QMessageBox.warning(self, "Invalid Selection", "Please enter both symbols!")
            return
        
        if primary == secondary:
            QMessageBox.warning(self, "Invalid Selection", "Please enter different symbols!")
            return
        
        # Log analysis
        self.add_log("="*70)
        self.add_log(f"🔍 ANALYZING PAIR: {primary} / {secondary}")
        self.add_log("="*70)
        
        # Load symbols from MT5 using SymbolLoader
        try:
            symbols = self.symbol_loader.load_pair(primary, secondary)
            
            self.add_log(f"📊 {primary}:")
            self.add_log(f"   Contract Size: {symbols['primary']['contract_size']}")
            self.add_log(f"   Min Lot: {symbols['primary']['min_lot']}")
            self.add_log(f"   Lot Step: {symbols['primary']['lot_step']}")
            self.add_log("")
            self.add_log(f"📊 {secondary}:")
            self.add_log(f"   Contract Size: {symbols['secondary']['contract_size']}")
            self.add_log(f"   Min Lot: {symbols['secondary']['min_lot']}")
            self.add_log(f"   Lot Step: {symbols['secondary']['lot_step']}")
            self.add_log("")
            
        except Exception as e:
            self.add_log(f"❌ Error loading symbols: {e}")
            self.add_log(f"   Check:")
            self.add_log(f"   1. MT5 is running and logged in")
            self.add_log(f"   2. Symbol names are correct")
            self.add_log(f"   3. Symbols are in Market Watch")
            self.add_log("")
            QMessageBox.critical(self, "Symbol Error", 
                                f"Could not load symbols:\n\n{e}")
            return
        
        # Show global settings info
        settings = self.settings_manager.get()
        self.add_log(f"⚙️  Global Settings (apply to ALL pairs):")
        self.add_log(f"   Entry: {settings.entry_threshold}, Exit: {settings.exit_threshold}")
        self.add_log(f"   Volume: {settings.volume_multiplier}x, Window: {settings.rolling_window_size}")
        self.add_log(f"   Max Positions: {settings.max_positions}, Risk: {settings.max_risk_pct}%")
        
        self.add_log("="*70)
        self.add_log(f"✅ Pair {primary}/{secondary} is ready for trading!")
        self.add_log(f"   Adjust settings in Settings tab if needed")
        self.add_log(f"   Then click 'Start Trading' to begin")
        self.add_log("="*70)
        
        self.statusBar.showMessage(f"Analysis complete: {primary}/{secondary}")
        
        # Show summary in message box
        msg = f"Pair Analysis: {primary} / {secondary}\n\n"
        msg += f"{primary}: Contract={symbols['primary']['contract_size']}\n"
        msg += f"{secondary}: Contract={symbols['secondary']['contract_size']}\n\n"
        
        if has_config:
            msg += "✅ Saved configuration found\n"
            msg += "Settings loaded from config file\n\n"
        else:
            msg += "⚠️ No saved configuration\n"
            msg += "Using current Settings tab values\n\n"
        
        msg += "Ready to trade!\n"
        msg += "Click 'Start Trading' when ready."
        
        QMessageBox.information(self, "Pair Analysis", msg)
    
    def toggle_trading(self):
        """Start or stop trading"""
        
        # CRITICAL: Check if thread exists and is running
        if self.trading_thread is not None and self.trading_thread.isRunning():
            # ========== STOP TRADING (NON-BLOCKING) ==========
            self.add_log("="*70)
            self.add_log("⏸️ STOPPING TRADING SYSTEM")
            self.add_log("="*70)
            
            # Disable stop button while stopping
            self.start_stop_btn.setEnabled(False)
            self.start_stop_btn.setText("⏸️ Stopping...")
            self.statusBar.showMessage("Stopping trading system...")
            
            # Create and start stop thread (non-blocking!)
            self.stop_thread = StopThread(self.trading_thread)
            self.stop_thread.log_message.connect(self.add_log)
            self.stop_thread.finished_signal.connect(self._on_stop_finished)
            self.stop_thread.start()
            
            return  # Done - stop happens in background!
        
        # ========== START TRADING ==========
        # Clean up any dead threads first
        if self.trading_thread is not None:
            self.trading_thread = None
        
        primary = self.primary_input.text().strip()
        secondary = self.secondary_input.text().strip()
        
        if not primary or not secondary or primary == secondary:
            QMessageBox.warning(self, "Invalid Selection", 
                                "Please enter valid, different symbols!")
            return
        
        # CRITICAL: Safety check - if symbols different from last run
        # This can happen if user somehow changes inputs while running (shouldn't be possible)
        # or if there's a UI bug
        if hasattr(self, '_last_symbols') and self._last_symbols:
            last_primary, last_secondary = self._last_symbols
            if (primary != last_primary or secondary != last_secondary):
                self.add_log("="*70)
                self.add_log(f"⚠️  SYMBOL CHANGE DETECTED!")
                self.add_log(f"   Previous: {last_primary}/{last_secondary}")
                self.add_log(f"   New: {primary}/{secondary}")
                self.add_log(f"   Starting with NEW symbols...")
                self.add_log("="*70)
        
        # Store current symbols for next time
        self._last_symbols = (primary, secondary)
        
        # Load symbols from MT5 (runtime!)
        self.add_log("="*70)
        self.add_log("🚀 STARTING TRADING SYSTEM")
        self.add_log("="*70)
        self.add_log(f"📊 Selected Pair: {primary} / {secondary}")
        self.add_log("🔄 Loading symbol info from MT5...")
        
        try:
            symbols = self.symbol_loader.load_pair(primary, secondary)
            self.add_log(f"✅ {primary}: contract_size={symbols['primary']['contract_size']}, min_lot={symbols['primary']['min_lot']}")
            self.add_log(f"✅ {secondary}: contract_size={symbols['secondary']['contract_size']}, min_lot={symbols['secondary']['min_lot']}")
        except Exception as e:
            self.add_log(f"❌ Failed to load symbols: {e}")
            QMessageBox.critical(self, "Symbol Error", 
                                f"Could not load symbols from MT5:\n\n{e}\n\n"
                                "Please check:\n"
                                "1. MT5 is running and logged in\n"
                                "2. Symbol names are correct\n"
                                "3. Symbols are in Market Watch")
            return
        
        # Get global settings
        settings = self.settings_manager.get()
        self.add_log(f"⚙️  Global Settings:")
        self.add_log(f"   Entry: {settings.entry_threshold}, Exit: {settings.exit_threshold}")
        self.add_log(f"   Volume: {settings.volume_multiplier}x, Window: {settings.rolling_window_size}")
        self.add_log(f"   Max Positions: {settings.max_positions}, Risk: {settings.max_risk_pct}%")
        self.add_log("="*70)
        
        # Update dashboard displays with NEW symbols
        self.add_log(f"🔄 Updating dashboard for {primary}/{secondary}...")
        # You can add dashboard update here if needed
        
        # Create trading config (combine symbols + settings)
        trading_config = {
            'symbols': symbols,
            'settings': settings.to_dict(),
            'primary_symbol': primary,
            'secondary_symbol': secondary
        }
        
        # Create and start trading thread
        self.trading_thread = TradingSystemThread(trading_config)
        self.trading_thread.log_message.connect(self.add_log)
        self.trading_thread.snapshot_update.connect(self.on_snapshot_update)  # ← NEW: Chart updates
        self.trading_thread.finished.connect(self._on_thread_finished)  # Handle cleanup
        self.trading_thread.start()
        
        # Auto-save config after successful start (không cần hỏi!)
        self.add_log("")
        self.add_log("💾 Auto-saving configuration...")
        try:
            # Update settings from current GUI values
            self.settings_manager.update(
                entry_threshold=self.entry_zscore_spin.value(),
                exit_threshold=self.exit_zscore_spin.value(),
                stop_loss_zscore=self.stop_zscore_spin.value(),
                max_positions=self.max_positions_spin.value(),
                volume_multiplier=self.volume_mult_spin.value(),
                rolling_window_size=self.window_spin.value(),
                update_interval=self.interval_spin.value(),
                hedge_drift_threshold=self.hedge_drift_spin.value(),
                max_position_pct=self.max_pos_pct_spin.value(),
                max_risk_pct=self.max_risk_pct_spin.value(),
                daily_loss_limit=self.daily_loss_spin.value(),
                scale_interval=self.scale_interval_spin.value(),
                initial_fraction=self.initial_fraction_spin.value(),
                min_adjustment_interval=self.min_adjust_interval_spin.value(),
                magic_number=self.magic_number_spin.value(),
                zscore_history_size=self.zscore_history_spin.value(),
                enable_pyramiding=self.pyramiding_check.isChecked(),
                enable_hedge_adjustment=self.hedge_adjust_check.isChecked()
            )
            self.settings_manager.save()
            self.add_log("✅ Configuration auto-saved for next time")
        except Exception as e:
            self.add_log(f"⚠️  Failed to auto-save config: {e}")
        
        self.add_log("="*70)
        
        # Update UI to RUNNING state
        self.start_stop_btn.setText("⏸️ Stop Trading")
        self.start_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.status_indicator.setText("🟢 Running")
        self.status_indicator.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.statusBar.showMessage(f"Trading {primary}/{secondary}...")
        
        # Disable symbol selection while running
        self.primary_input.setEnabled(False)
        self.secondary_input.setEnabled(False)
        # self.analyze_btn.setEnabled(False)  # Button removed
        
        # Load historical data into chart (after 3 seconds to let system bootstrap)
        self.load_chart_historical_data()
    
    def _on_thread_finished(self):
        """Handle thread finished signal"""
        self.add_log("📍 Trading thread has finished")
        
        # If button still shows "Stop", update it
        if self.start_stop_btn.text() == "⏸️ Stop Trading":
            self.start_stop_btn.setText("▶️ Start Trading")
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 4px;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
            self.status_indicator.setText("⚫ Stopped")
            self.status_indicator.setStyleSheet("color: #7f8c8d; font-weight: bold;")
            
            # Re-enable controls
            self.primary_input.setEnabled(True)
            self.secondary_input.setEnabled(True)
            # self.analyze_btn.setEnabled(True)  # Button removed
    
    def _on_stop_finished(self, graceful: bool):
        """Called when stop thread finishes (non-blocking!)"""
        # Log result
        if graceful:
            self.add_log("✅ Trading system stopped gracefully")
        else:
            self.add_log("⚠️  Trading system force stopped")
        self.add_log("="*70)
        
        # Clear thread reference
        self.trading_thread = None
        
        # Update UI to STOPPED state
        self.start_stop_btn.setEnabled(True)
        self.start_stop_btn.setText("▶️ Start Trading")
        self.start_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.status_indicator.setText("⚫ Stopped")
        self.status_indicator.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        self.statusBar.showMessage("Trading system stopped")
        
        # Re-enable symbol selection
        self.primary_input.setEnabled(True)
        self.secondary_input.setEnabled(True)
        
        # Stop chart updates
        if hasattr(self, 'chart_widget'):
            self.chart_widget.stop_auto_update()
    
    def on_snapshot_update(self, snapshot):
        """Handle new market snapshot for chart updates"""
        if hasattr(self, 'chart_widget') and snapshot:
            self.chart_widget.add_realtime_data(snapshot)
    
    def load_chart_historical_data(self):
        """Load historical data into chart when trading starts"""
        if hasattr(self, 'chart_widget') and hasattr(self, 'trading_thread'):
            if self.trading_thread and self.trading_thread.trading_system:
                # Wait a bit for trading system to bootstrap
                QTimer.singleShot(3000, lambda: self._do_load_chart_data())
    
    def _do_load_chart_data(self):
        """Actually load the chart data"""
        if hasattr(self, 'trading_thread') and self.trading_thread and self.trading_thread.trading_system:
            self.chart_widget.load_historical_data(self.trading_thread.trading_system)
            self.chart_widget.start_auto_update()
    
    def get_current_pair_config(self) -> PairConfig:
        """Get current pair configuration from GUI"""
        # Get symbols from text inputs (not comboboxes!)
        primary = self.primary_input.text().strip()
        secondary = self.secondary_input.text().strip()
        
        # Validate symbols are not empty
        if not primary or not secondary:
            self.add_log("⚠️  Please enter both primary and secondary symbols!")
            raise ValueError("Symbol names cannot be empty")
        
        # Get symbol configs from MT5
        primary_symbol = self.config_manager.get_symbol(primary)
        secondary_symbol = self.config_manager.get_symbol(secondary)
        
        # Log symbol info
        if primary_symbol:
            self.add_log(f"✅ {primary}: Contract size = {primary_symbol.contract_size}")
        else:
            self.add_log(f"⚠️  {primary}: Using default specs (check symbol name in MT5)")
        
        if secondary_symbol:
            self.add_log(f"✅ {secondary}: Contract size = {secondary_symbol.contract_size}")
        else:
            self.add_log(f"⚠️  {secondary}: Using default specs (check symbol name in MT5)")
        
        return PairConfig(
            name=f"{primary}_{secondary}",
            primary_symbol=primary,
            secondary_symbol=secondary,
            primary_contract_size=primary_symbol.contract_size if primary_symbol else 1.0,
            secondary_contract_size=secondary_symbol.contract_size if secondary_symbol else 1.0,
            entry_threshold=self.entry_zscore_spin.value(),
            exit_threshold=self.exit_zscore_spin.value(),
            stop_loss_zscore=self.stop_zscore_spin.value(),
            max_positions=self.max_positions_spin.value(),
            volume_multiplier=self.volume_mult_spin.value(),
            rolling_window_size=self.window_spin.value(),
            update_interval=self.interval_spin.value(),
            hedge_drift_threshold=self.hedge_drift_spin.value(),
            max_position_pct=self.max_pos_pct_spin.value(),
            max_risk_pct=self.max_risk_pct_spin.value(),
            daily_loss_limit=self.daily_loss_spin.value(),
            enable_pyramiding=self.pyramiding_check.isChecked(),
            enable_hedge_adjustment=self.hedge_adjust_check.isChecked(),
            # Advanced settings
            scale_interval=self.scale_interval_spin.value(),
            initial_fraction=self.initial_fraction_spin.value(),
            min_adjustment_interval=self.min_adjust_interval_spin.value(),
            magic_number=self.magic_number_spin.value(),
            zscore_history_size=self.zscore_history_spin.value(),
            position_data_dir="positions"  # Fixed value
        )
    
    def update_display(self):
        """Update all displays with current data"""
        if not self.trading_thread or not self.trading_thread.isRunning():
            return
        
        try:
            # Get status from trading system
            status = self.trading_thread.get_status()
            
            if status:
                # Update statistics
                zscore = status.get('zscore', 0.0)
                self.zscore_label.setText(f"{zscore:+.3f}")
                
                # Color code z-score
                if abs(zscore) > 2.5:
                    self.zscore_label.setStyleSheet("color: #e74c3c; font-weight: bold;")  # Red
                elif abs(zscore) > 2.0:
                    self.zscore_label.setStyleSheet("color: #e67e22; font-weight: bold;")  # Orange
                else:
                    self.zscore_label.setStyleSheet("color: #2ecc71; font-weight: bold;")  # Green
                
                self.correlation_label.setText(f"{status.get('correlation', 0.0):.3f}")
                self.hedge_ratio_label.setText(f"{status.get('hedge_ratio', 0.0):.4f}")
                self.spread_label.setText(f"{status.get('spread', 0.0):.2f}")
                
                # Update P&L
                total_pnl = status.get('total_pnl', 0.0)
                self.pnl_label.setText(f"${total_pnl:,.2f}")
                
                # Color code P&L
                if total_pnl > 0:
                    self.pnl_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                elif total_pnl < 0:
                    self.pnl_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.pnl_label.setStyleSheet("color: #ecf0f1; font-weight: bold;")
                
                # Update signal
                if abs(zscore) > 2.0:
                    if zscore > 0:
                        self.signal_label.setText("SHORT")
                        self.signal_label.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px; border-radius: 3px; font-weight: bold;")
                    else:
                        self.signal_label.setText("LONG")
                        self.signal_label.setStyleSheet("background-color: #27ae60; color: white; padding: 5px; border-radius: 3px; font-weight: bold;")
                else:
                    self.signal_label.setText("HOLD")
                    self.signal_label.setStyleSheet("background-color: #7f8c8d; color: white; padding: 5px; border-radius: 3px; font-weight: bold;")
                
                # Update model metrics
                self.mean_label.setText(f"{status.get('spread_mean', 0.0):.2f}")
                self.std_label.setText(f"{status.get('spread_std', 0.0):.2f}")
                self.positions_count_label.setText(f"{status.get('open_positions', 0)} / {status.get('closed_positions', 0)}")
                
                # Update new statistics
                self.max_zscore_label.setText(f"{status.get('max_zscore', 0.0):.3f}")
                self.min_mean_label.setText(f"{status.get('min_mean', 0.0):.2f}")
                self.max_mean_label.setText(f"{status.get('max_mean', 0.0):.2f}")
                
                # ========== Update MT5 Risk Management Panel ==========
                mt5_balance = status.get('mt5_balance', 0.0)
                mt5_equity = status.get('mt5_equity', 0.0)
                mt5_profit = status.get('mt5_profit', 0.0)
                
                # DEBUG: Log what we're setting
                logger.debug(f"GUI: Setting MT5 labels - Balance=${mt5_balance:,.2f}, "
                           f"Equity=${mt5_equity:,.2f}, Profit=${mt5_profit:,.2f}")
                
                self.mt5_balance_label.setText(f"${mt5_balance:,.2f}")
                self.mt5_balance_label.repaint()  # Force repaint
                self.mt5_equity_label.setText(f"${mt5_equity:,.2f}")
                self.mt5_profit_label.setText(f"${mt5_profit:,.2f}")
                
                # Also log if balance is 0
                if mt5_balance == 0.0:
                    logger.warning(f"MT5 Balance is $0.00! Check if MT5RiskMonitor is working")
                
                # Color code MT5 profit
                if mt5_profit > 0:
                    self.mt5_profit_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                elif mt5_profit < 0:
                    self.mt5_profit_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.mt5_profit_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
                
                # Margin info
                self.mt5_margin_label.setText(f"${status.get('mt5_margin', 0.0):,.2f}")
                self.mt5_margin_free_label.setText(f"${status.get('mt5_margin_free', 0.0):,.2f}")
                
                mt5_margin_level = status.get('mt5_margin_level', 0.0)
                self.mt5_margin_level_label.setText(f"{mt5_margin_level:.1f}%")
                
                # Color code margin level
                if mt5_margin_level > 200:
                    self.mt5_margin_level_label.setStyleSheet("color: #27ae60; font-weight: bold;")  # Safe
                elif mt5_margin_level > 100:
                    self.mt5_margin_level_label.setStyleSheet("color: #f39c12; font-weight: bold;")  # Warning
                else:
                    self.mt5_margin_level_label.setStyleSheet("color: #e74c3c; font-weight: bold;")  # Danger
                
                # Position lots
                mt5_primary_lots = status.get('mt5_primary_lots', 0.0)
                mt5_secondary_lots = status.get('mt5_secondary_lots', 0.0)
                
                self.mt5_primary_lots_label.setText(f"{mt5_primary_lots:+.4f}")
                self.mt5_secondary_lots_label.setText(f"{mt5_secondary_lots:+.4f}")
                self.mt5_positions_label.setText(f"{status.get('mt5_positions', 0)}")
                
                # CRITICAL: Hedge Imbalance
                hedge_imbalance = status.get('mt5_hedge_imbalance', 0.0)
                hedge_imbalance_pct = status.get('mt5_hedge_imbalance_pct', 0.0)
                hedge_imbalance_value = status.get('mt5_hedge_imbalance_value', 0.0)
                
                self.mt5_hedge_imbalance_label.setText(f"{hedge_imbalance:+.4f} lots")
                self.mt5_hedge_imbalance_pct_label.setText(f"{hedge_imbalance_pct:+.2%}")
                self.mt5_hedge_imbalance_value_label.setText(f"${hedge_imbalance_value:,.2f}")
                
                # Color code imbalance based on severity
                imbalance_severity = abs(hedge_imbalance_pct)
                if imbalance_severity < 0.02:  # < 2%
                    imbalance_color = "#27ae60"  # Green - good
                elif imbalance_severity < 0.05:  # 2-5%
                    imbalance_color = "#f39c12"  # Orange - warning
                else:  # > 5%
                    imbalance_color = "#e74c3c"  # Red - danger
                
                self.mt5_hedge_imbalance_label.setStyleSheet(f"color: {imbalance_color}; font-weight: bold;")
                self.mt5_hedge_imbalance_pct_label.setStyleSheet(f"color: {imbalance_color}; font-weight: bold;")
                
                # ========== NEW: Stop Loss & Risk Amount ==========
                mt5_max_risk_pct = status.get('mt5_max_risk_pct', 20.0)
                mt5_stop_loss_level = status.get('mt5_stop_loss_level', 0.0)
                mt5_risk_amount = status.get('mt5_risk_amount', 0.0)
                mt5_distance_to_sl_pct = status.get('mt5_distance_to_sl_pct', 0.0)
                
                self.mt5_max_risk_label.setText(f"{mt5_max_risk_pct:.1f}%")
                self.mt5_stop_loss_label.setText(f"${mt5_stop_loss_level:,.2f}")
                self.mt5_risk_amount_label.setText(f"${mt5_risk_amount:,.2f}")
                self.mt5_distance_to_sl_label.setText(f"{mt5_distance_to_sl_pct:.1f}%")
                
                # Color code distance to SL
                if mt5_distance_to_sl_pct > 15:  # > 15% away from SL
                    sl_color = "#27ae60"  # Green - safe
                elif mt5_distance_to_sl_pct > 5:  # 5-15%
                    sl_color = "#f39c12"  # Orange - warning
                else:  # < 5%
                    sl_color = "#e74c3c"  # Red - danger!
                
                self.mt5_distance_to_sl_label.setStyleSheet(f"color: {sl_color}; font-weight: bold;")
                # ========== END Stop Loss Update ==========
                
                # ========== END MT5 Risk Update ==========
                
                # ========== Update P&L Attribution Panel ==========
                # Get attribution from status (if available)
                attr_spread_pnl = status.get('attr_spread_pnl', 0.0)
                attr_spread_pct = status.get('attr_spread_pct', 0.0)
                attr_mean_pnl = status.get('attr_mean_pnl', 0.0)
                attr_mean_pct = status.get('attr_mean_pct', 0.0)
                attr_directional_pnl = status.get('attr_directional_pnl', 0.0)
                attr_directional_pct = status.get('attr_directional_pct', 0.0)
                attr_hedge_pnl = status.get('attr_hedge_pnl', 0.0)
                attr_hedge_pct = status.get('attr_hedge_pct', 0.0)
                attr_costs = status.get('attr_costs', 0.0)
                attr_costs_pct = status.get('attr_costs_pct', 0.0)
                attr_slippage = status.get('attr_slippage', 0.0)
                attr_slippage_pct = status.get('attr_slippage_pct', 0.0)
                attr_rebalance = status.get('attr_rebalance', 0.0)
                attr_rebalance_pct = status.get('attr_rebalance_pct', 0.0)
                attr_hedge_quality = status.get('attr_hedge_quality', 0.0)
                attr_purity = status.get('attr_purity', 0.0)
                attr_classification = status.get('attr_classification', 'NO DATA')
                
                # Update labels
                self.attr_spread_pnl_label.setText(f"${attr_spread_pnl:,.2f}")
                self.attr_spread_pct_label.setText(f"{attr_spread_pct:.1f}%")
                
                self.attr_mean_pnl_label.setText(f"${attr_mean_pnl:,.2f}")
                self.attr_mean_pct_label.setText(f"{attr_mean_pct:.1f}%")
                
                self.attr_directional_pnl_label.setText(f"${attr_directional_pnl:,.2f}")
                self.attr_directional_pct_label.setText(f"{attr_directional_pct:.1f}%")
                
                self.attr_hedge_pnl_label.setText(f"${attr_hedge_pnl:,.2f}")
                self.attr_hedge_pct_label.setText(f"{attr_hedge_pct:.1f}%")
                
                self.attr_costs_label.setText(f"${attr_costs:,.2f}")
                self.attr_costs_pct_label.setText(f"{attr_costs_pct:.1f}%")
                
                self.attr_slippage_label.setText(f"${attr_slippage:,.2f}")
                self.attr_slippage_pct_label.setText(f"{attr_slippage_pct:.1f}%")
                
                self.attr_rebalance_label.setText(f"${attr_rebalance:,.2f}")
                self.attr_rebalance_pct_label.setText(f"{attr_rebalance_pct:.1f}%")
                
                # Quality metrics
                if attr_hedge_quality > 0:
                    self.attr_hedge_quality_label.setText(f"{attr_hedge_quality:.1%}")
                else:
                    self.attr_hedge_quality_label.setText("--")
                
                if attr_purity != 0:
                    self.attr_purity_label.setText(f"{attr_purity:.1f}%")
                else:
                    self.attr_purity_label.setText("--")
                
                self.attr_class_label.setText(attr_classification)
                
                # Color coding
                # Spread P&L - Blue if positive
                if attr_spread_pnl > 0:
                    self.attr_spread_pnl_label.setStyleSheet("color: #3498db; font-weight: bold;")
                elif attr_spread_pnl < 0:
                    self.attr_spread_pnl_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.attr_spread_pnl_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
                
                # Directional - Warning if high percentage
                if abs(attr_directional_pct) > 50:
                    self.attr_directional_pnl_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                elif abs(attr_directional_pct) > 20:
                    self.attr_directional_pnl_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                else:
                    self.attr_directional_pnl_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                
                # Hedge Quality
                if attr_hedge_quality > 0.8:
                    self.attr_hedge_quality_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                elif attr_hedge_quality > 0.6:
                    self.attr_hedge_quality_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                elif attr_hedge_quality > 0:
                    self.attr_hedge_quality_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.attr_hedge_quality_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
                
                # Classification
                if attr_classification == "PURE_STAT_ARB":
                    self.attr_class_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                elif attr_classification == "DIRECTIONAL":
                    self.attr_class_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                elif attr_classification == "NO DATA":
                    self.attr_class_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
                else:
                    self.attr_class_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                
                # ========== END Attribution Update ==========
                
                # Update timestamp
                self.last_update_label.setText(datetime.now().strftime("%H:%M:%S"))
            
            # Update positions table
            positions = self.trading_thread.get_positions()
            self.positions_table.setRowCount(len(positions))
            
            for i, pos in enumerate(positions):
                self.positions_table.setItem(i, 0, QTableWidgetItem(pos['id']))
                self.positions_table.setItem(i, 1, QTableWidgetItem(pos['symbol']))
                self.positions_table.setItem(i, 2, QTableWidgetItem(pos['side']))
                self.positions_table.setItem(i, 3, QTableWidgetItem(f"{pos['quantity']:.4f}"))
                self.positions_table.setItem(i, 4, QTableWidgetItem(f"{pos['entry_price']:.3f}"))
                self.positions_table.setItem(i, 5, QTableWidgetItem(f"{pos['current_price']:.3f}"))
                
                # Color code P&L
                pnl_item = QTableWidgetItem(f"${pos['unrealized_pnl']:,.2f}")
                if pos['unrealized_pnl'] > 0:
                    pnl_item.setForeground(QColor("#27ae60"))
                elif pos['unrealized_pnl'] < 0:
                    pnl_item.setForeground(QColor("#e74c3c"))
                self.positions_table.setItem(i, 6, pnl_item)
                
                self.positions_table.setItem(i, 7, QTableWidgetItem(pos['opened_at']))
                
                entry_z = pos.get('metadata', {}).get('entry_zscore', 0.0)
                self.positions_table.setItem(i, 8, QTableWidgetItem(f"{entry_z:.2f}"))
                self.positions_table.setItem(i, 9, QTableWidgetItem("Active"))
                
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def save_settings(self):
        """
        Save current settings to configuration
        These settings apply to ALL pairs!
        """
        # Update settings from GUI
        self.settings_manager.update(
            # Trading
            entry_threshold=self.entry_zscore_spin.value(),
            exit_threshold=self.exit_zscore_spin.value(),
            stop_loss_zscore=self.stop_zscore_spin.value(),
            max_positions=self.max_positions_spin.value(),
            volume_multiplier=self.volume_mult_spin.value(),
            
            # Model
            rolling_window_size=self.window_spin.value(),
            update_interval=self.interval_spin.value(),
            hedge_drift_threshold=self.hedge_drift_spin.value(),
            
            # Risk
            max_position_pct=self.max_pos_pct_spin.value(),
            max_risk_pct=self.max_risk_pct_spin.value(),
            daily_loss_limit=self.daily_loss_spin.value(),
            
            # Advanced
            scale_interval=self.scale_interval_spin.value(),
            initial_fraction=self.initial_fraction_spin.value(),
            min_adjustment_interval=self.min_adjust_interval_spin.value(),
            magic_number=self.magic_number_spin.value(),
            zscore_history_size=self.zscore_history_spin.value(),
            
            # Features
            enable_pyramiding=self.pyramiding_check.isChecked(),
            enable_hedge_adjustment=self.hedge_adjust_check.isChecked()
        )
        
        # Save to file
        self.settings_manager.save()
        
        # Update displays
        settings = self.settings_manager.get()
        self.entry_threshold_display.setText(f"{settings.entry_threshold:.1f}")
        self.exit_threshold_display.setText(f"{settings.exit_threshold:.1f}")
        self.window_size_display.setText(f"{settings.rolling_window_size}")
        
        # Log details
        self.add_log(f"💾 Global settings saved!")
        self.add_log(f"   Entry: {settings.entry_threshold}, Exit: {settings.exit_threshold}")
        self.add_log(f"   Volume: {settings.volume_multiplier}x, Window: {settings.rolling_window_size}")
        self.add_log(f"   Max Positions: {settings.max_positions}, Risk: {settings.max_risk_pct}%")
        self.add_log(f"   ✅ These settings apply to ALL symbol pairs!")
        self.add_log(f"   Saved to: config/trading_settings.yaml")
        
        QMessageBox.information(self, "Settings Saved", 
                                "Global settings saved successfully!\n\n"
                                "These settings will apply to ALL symbol pairs.\n\n"
                                "File: config/trading_settings.yaml")
    
    def apply_settings(self):
        """Apply current settings to running system"""
        if not self.trading_thread or not self.trading_thread.isRunning():
            QMessageBox.warning(self, "Not Running", 
                                "Trading system is not running. Start trading first!")
            return
        
        # Get new settings from GUI
        settings = self.settings_manager.get()
        
        if self.trading_thread.trading_system:
            sys = self.trading_thread.trading_system
            
            # Check if rolling window changed (requires recalculation)
            old_window = sys.market_data.rolling_window_size
            new_window = self.window_spin.value()
            window_changed = (old_window != new_window)
            
            if window_changed:
                # Window size changed - need to restart and recalculate!
                reply = QMessageBox.question(
                    self, 
                    "Restart Required",
                    f"Rolling window changed ({old_window} → {new_window}).\n\n"
                    "This requires stopping and restarting the system to recalculate from scratch.\n\n"
                    "Restart now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.add_log("="*70)
                    self.add_log("🔄 RESTARTING SYSTEM (Rolling Window Changed)")
                    self.add_log(f"   Old Window: {old_window} → New Window: {new_window}")
                    self.add_log("="*70)
                    
                    # Stop current system
                    self.toggle_trading()  # Stop
                    
                    # Wait a bit for clean shutdown
                    import time
                    time.sleep(1)
                    
                    # Start with new settings
                    self.toggle_trading()  # Start with new config
                    
                    self.add_log("✅ System restarted with new rolling window")
                else:
                    self.add_log("⚠️  Rolling window change cancelled")
                return
            
            # Apply settings to running system (hot-reload)
            self.add_log("="*70)
            self.add_log("🔄 APPLYING SETTINGS (Hot-Reload)")
            self.add_log("="*70)
            
            # Signal generator
            entry = self.entry_zscore_spin.value()
            exit_val = self.exit_zscore_spin.value()
            stop = self.stop_zscore_spin.value()
            sys.signal_generator.entry_threshold = entry
            sys.signal_generator.exit_threshold = exit_val
            sys.signal_generator.stop_loss_zscore = stop
            self.add_log(f"   Entry: {entry}, Exit: {exit_val}, Stop: {stop}")
            
            # Rebalancer
            hedge_drift = self.hedge_drift_spin.value()
            enable_hedge = self.hedge_adjust_check.isChecked()
            sys.rebalancer.hedge_drift_threshold = hedge_drift
            sys.rebalancer.enable_hedge_adjustment = enable_hedge
            self.add_log(f"   Hedge Drift: {hedge_drift}, Adjustment: {enable_hedge}")
            
            # Risk settings
            if hasattr(sys, 'position_sizer'):
                max_pos = self.max_pos_pct_spin.value()
                max_risk = self.max_risk_pct_spin.value()
                sys.position_sizer.max_position_pct = max_pos
                sys.position_sizer.max_risk_pct = max_risk
                self.add_log(f"   Position: {max_pos}%, Risk: {max_risk}%")
            
            # Volume multiplier (affects future trades)
            vol_mult = self.volume_mult_spin.value()
            sys.volume_multiplier = vol_mult
            self.add_log(f"   Volume Multiplier: {vol_mult}x")
            
            # Update display labels
            self.entry_threshold_display.setText(f"{entry:.1f}")
            self.exit_threshold_display.setText(f"{exit_val:.1f}")
            self.window_size_display.setText(f"{new_window}")
            
            self.add_log("="*70)
            self.add_log("✅ Settings applied to running system")
            self.add_log("="*70)
            
            QMessageBox.information(self, "Settings Applied", 
                                    "Settings have been applied!\n\n"
                                    "New trades will use updated parameters.")
    
    def add_log(self, message: str):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """Clear all logs"""
        self.log_display.clear()
        self.add_log("Logs cleared")
    
    def closeEvent(self, event):
        """Handle window close event - ALWAYS stop trading thread"""
        if self.trading_thread and self.trading_thread.isRunning():
            reply = QMessageBox.question(self, "Confirm Exit",
                                          "Trading system is running. Stop and exit?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.add_log("🛑 Stopping trading system before exit...")
                self.trading_thread.stop()
                
                # Wait up to 10 seconds for graceful stop
                if not self.trading_thread.wait(10000):
                    self.add_log("⚠️  Force terminating thread...")
                    self.trading_thread.terminate()
                    self.trading_thread.wait(2000)
                
                self.add_log("✅ Trading system stopped - safe to exit")
                event.accept()
            else:
                # User chose not to exit
                event.ignore()
        else:
            # No trading thread running - safe to exit
            event.accept()
    


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("Pair Trading System - Professional")
    app.setOrganizationName("Professional Trading")
    
    # Create and show window
    window = PairTradingGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
