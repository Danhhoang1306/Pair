"""
Example: How to Use Assets
"""

# ==================== METHOD 1: Import Everything ====================
from assets import *

# Now you have access to:
# - All color constants
# - DARCULA_THEME_QSS stylesheet
# - All config constants
# - Helper functions

# Example: Apply theme to main window
from PyQt6.QtWidgets import QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Apply Darcula theme
        apply_theme(self)
        
        # Or manually:
        # self.setStyleSheet(DARCULA_THEME_QSS)


# ==================== METHOD 2: Import Specific Items ====================
from assets.styles import BG_DARKER, TEXT_NORMAL, ACCENT_BLUE, get_pnl_color
from assets.config import DEFAULT_ENTRY_ZSCORE, get_pair_config

# Use colors
background_color = BG_DARKER
text_color = TEXT_NORMAL

# Use config
entry_threshold = DEFAULT_ENTRY_ZSCORE
pair_info = get_pair_config('XAU_XAG')


# ==================== METHOD 3: Import Modules ====================
from assets import styles, config

# Use with module prefix
my_label.setStyleSheet(f"color: {styles.TEXT_BRIGHT};")
entry_z = config.DEFAULT_ENTRY_ZSCORE


# ==================== COMMON USAGE PATTERNS ====================

# 1. Set label color based on P&L
pnl_value = -150.50
color = get_pnl_color(pnl_value)  # Returns CHART_BEAR (red)
my_label.setStyleSheet(f"color: {color};")

# 2. Get status color
status_color = get_status_color('success')  # Returns STATUS_SUCCESS (green)
status_label.setStyleSheet(f"color: {status_color};")

# 3. Create custom button style
button.setStyleSheet(f"""
    QPushButton {{
        background-color: {ACCENT_BLUE};
        color: {TEXT_BRIGHT};
        border: 1px solid {BORDER_MEDIUM};
        border-radius: 3px;
        padding: 8px 16px;
    }}
    QPushButton:hover {{
        background-color: {ACCENT_BLUE_HOVER};
    }}
""")

# 4. Get pair configuration
btc_eth_config = get_pair_config('BTC_ETH')
print(f"Risk Level: {btc_eth_config['risk_level']}")  # HIGH
print(f"Recommended Entry: {btc_eth_config['recommended_entry_zscore']}")  # 2.5

# 5. Get symbol info
xau_info = get_symbol_config('XAUUSD')
print(f"Contract Size: {xau_info['contract_size']}")  # 100.0
print(f"Min Lot: {xau_info['min_lot']}")  # 0.01

# 6. Apply theme to entire application
from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
app.setStyleSheet(DARCULA_THEME_QSS)

# 7. Use in QLabel with custom class
label = QLabel("Title Text")
label.setProperty("class", "title")  # Uses QLabel[class="title"] style

# 8. Access all defaults at once
defaults = get_default_config()
print(defaults)
"""
{
    'entry_zscore': 2.0,
    'exit_zscore': 0.5,
    'max_positions': 10,
    ...
}
"""


# ==================== QUICK REFERENCE ====================

"""
COLOR CATEGORIES:
- BG_* : Background colors (darkest to lightest)
- TEXT_* : Text colors (disabled to bright)
- BORDER_* : Border colors
- ACCENT_* : Accent/highlight colors
- STATUS_* : Status indicator colors
- CHART_* : Chart-specific colors

CONFIG CATEGORIES:
- DEFAULT_* : Default trading parameters
- *_CONFIG : Configuration dictionaries
- SYMBOL_CONFIGS : Per-symbol settings
- PAIR_CONFIGS : Per-pair settings

FUNCTIONS:
- apply_theme(widget) : Apply full Darcula theme
- get_pnl_color(value) : Get color for P&L value
- get_status_color(status) : Get color for status
- get_pair_config(name) : Get pair configuration
- get_symbol_config(symbol) : Get symbol configuration
- get_default_config() : Get all defaults
"""
