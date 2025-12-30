"""Statistical models"""
from .cointegration import CointegrationTest, CointegrationResult, quick_test
from .hedge_ratios import HedgeRatioCalculator, HedgeRatioResult, quick_ols, quick_optimal
from .volatility import VolatilityModel, VolatilityResult, quick_garch, quick_ewma

__all__ = [
    'CointegrationTest',
    'CointegrationResult',
    'quick_test',
    'HedgeRatioCalculator',
    'HedgeRatioResult',
    'quick_ols',
    'quick_optimal',
    'VolatilityModel',
    'VolatilityResult',
    'quick_garch',
    'quick_ewma',
]
