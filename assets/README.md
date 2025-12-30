# Assets Folder

Centralized styles and configuration for the Pair Trading System.

## 📁 Structure

```
assets/
├── darcula_theme.css        # PyCharm Darcula theme stylesheet
├── default_config.yaml       # Default trading parameters
├── symbols_pairs.yaml        # Symbol and pair configurations
├── styles.py                 # Python color constants and helper functions
├── __init__.py               # Package initialization
└── README.md                 # This file
```

---

## 🎨 Styles

### **darcula_theme.css**

Complete PyCharm Darcula theme CSS stylesheet.

**Usage in Python:**
```python
from assets import DARCULA_THEME_QSS
widget.setStyleSheet(DARCULA_THEME_QSS)
```

**Or apply to entire app:**
```python
from PyQt6.QtWidgets import QApplication
from assets import DARCULA_THEME_QSS

app = QApplication(sys.argv)
app.setStyleSheet(DARCULA_THEME_QSS)
```

### **styles.py**

Python constants for programmatic color access.

**Usage:**
```python
from assets.styles import (
    BG_DARKER,        # #2B2B2B
    TEXT_NORMAL,      # #A9B7C6
    ACCENT_BLUE,      # #3592C4
    CHART_BULL,       # #6A8759
    CHART_BEAR,       # #BC3F3C
    get_pnl_color,    # Function
    apply_theme       # Function
)

# Use in code
label.setStyleSheet(f"color: {CHART_BULL};")
color = get_pnl_color(pnl_value)
```

---

## ⚙️ Configuration Files

### **default_config.yaml**

Default trading parameters and system settings.

**Contents:**
- Entry/Exit thresholds
- Position sizing
- Risk management
- Rebalancing settings
- MT5, logging, chart, GUI configs
- Attribution settings
- Risk limits
- Backtest parameters

**Usage:**
```python
import yaml

with open('assets/default_config.yaml') as f:
    config = yaml.safe_load(f)
    
entry_z = config['entry_zscore']  # 2.0
max_pos = config['max_positions']  # 10
```

### **symbols_pairs.yaml**

Symbol specifications and trading pair configurations.

**Contents:**
- Symbol specs (XAUUSD, XAGUSD, BTCUSD, ETHUSD, EURUSD, GBPUSD)
- Trading pairs (XAU_XAG, BTC_ETH, EUR_GBP)
- Risk tiers
- Recommended settings per pair

**Usage:**
```python
import yaml

with open('assets/symbols_pairs.yaml') as f:
    data = yaml.safe_load(f)
    
# Get symbol info
xau = data['symbols']['XAUUSD']
print(xau['contract_size'])  # 100.0

# Get pair info
btc_eth = data['pairs']['BTC_ETH']
print(btc_eth['risk_level'])  # HIGH
print(btc_eth['recommended_entry_zscore'])  # 2.5
```

---

## 🎯 Benefits

### **1. Centralized**
All styles and config in one place

### **2. Maintainable**
Easy to update colors or settings

### **3. Flexible**
- CSS for themes
- YAML for configuration
- Python for programmatic access

### **4. Professional**
PyCharm Darcula theme - industry standard

---

## 📝 Notes

- **CSS files** are loaded by `styles.py` automatically
- **YAML files** need to be loaded manually with `yaml.safe_load()`
- **Color constants** in `styles.py` match CSS values
- All files use UTF-8 encoding

---

## 🔄 Updating

### To Change Theme:
1. Edit `darcula_theme.css`
2. Restart application

### To Change Defaults:
1. Edit `default_config.yaml`
2. Reload config in application

### To Add Symbols/Pairs:
1. Edit `symbols_pairs.yaml`
2. Add to appropriate section
3. Reload in application
