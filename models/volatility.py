"""
Volatility Modeling Module
Calculate and forecast volatility for risk management

Includes:
- GARCH(1,1) volatility
- EWMA (Exponentially Weighted Moving Average)
- Rolling volatility
- Realized volatility
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

# GARCH modeling
from arch import arch_model

logger = logging.getLogger(__name__)


@dataclass
class VolatilityResult:
    """Results from volatility calculation"""
    current_vol: float
    annualized_vol: float
    vol_series: pd.Series
    method: str
    timestamp: datetime
    metadata: Dict = None
    
    def __str__(self):
        return (f"Volatility Result:\n"
                f"  Method: {self.method}\n"
                f"  Current: {self.current_vol:.4%}\n"
                f"  Annualized: {self.annualized_vol:.4%}")


class VolatilityModel:
    """
    Calculate volatility using multiple methods
    
    Example:
        >>> vol_model = VolatilityModel()
        >>> result = vol_model.calculate_garch(returns)
        >>> print(f"Current vol: {result.current_vol:.2%}")
    """
    
    def __init__(self,
                 periods_per_year: int = 252):
        """
        Initialize volatility model
        
        Args:
            periods_per_year: Trading periods per year (252 for daily, 252*24 for hourly)
        """
        self.periods_per_year = periods_per_year
        
        logger.info(f"VolatilityModel initialized (periods_per_year={periods_per_year})")
    
    def calculate_garch(self,
                       returns: pd.Series,
                       p: int = 1,
                       q: int = 1,
                       forecast_horizon: int = 1) -> VolatilityResult:
        """
        Calculate volatility using GARCH model
        
        GARCH(p,q) model:
        sigma²[t] = omega + Sigmaalpha[i]·epsilon²[t-i] + Sigmabeta[j]·sigma²[t-j]
        
        Most common: GARCH(1,1)
        sigma²[t] = omega + alpha·epsilon²[t-1] + beta·sigma²[t-1]
        
        Args:
            returns: Return series
            p: ARCH order
            q: GARCH order
            forecast_horizon: Forecast periods ahead
            
        Returns:
            VolatilityResult
        """
        logger.info(f"Calculating GARCH({p},{q}) volatility...")
        
        # Remove NaN values
        returns_clean = returns.dropna()
        
        # Scale returns to percentage
        returns_pct = returns_clean * 100
        
        # Fit GARCH model
        model = arch_model(
            returns_pct,
            vol='Garch',
            p=p,
            q=q,
            rescale=False
        )
        
        try:
            results = model.fit(disp='off', show_warning=False)
            
            # Get conditional volatility
            conditional_vol = results.conditional_volatility / 100  # Back to decimal
            
            # Forecast
            forecast = results.forecast(horizon=forecast_horizon)
            forecast_variance = forecast.variance.values[-1, 0]
            forecast_vol = np.sqrt(forecast_variance) / 100  # Back to decimal
            
            # Current volatility (last value)
            current_vol = conditional_vol.iloc[-1]
            
            # Annualize
            annualized_vol = current_vol * np.sqrt(self.periods_per_year)
            
            result = VolatilityResult(
                current_vol=current_vol,
                annualized_vol=annualized_vol,
                vol_series=conditional_vol,
                method=f'GARCH({p},{q})',
                timestamp=datetime.now(),
                metadata={
                    'omega': results.params['omega'],
                    'alpha': results.params[f'alpha[{p}]'],
                    'beta': results.params[f'beta[{q}]'],
                    'aic': results.aic,
                    'bic': results.bic,
                    'forecast_vol': forecast_vol,
                    'forecast_horizon': forecast_horizon
                }
            )
            
            logger.debug(f"GARCH vol: {current_vol:.4%} (annualized: {annualized_vol:.4%})")
            
            return result
            
        except Exception as e:
            logger.error(f"GARCH fitting failed: {e}")
            raise
    
    def calculate_ewma(self,
                      returns: pd.Series,
                      lambda_param: float = 0.94) -> VolatilityResult:
        """
        Calculate EWMA (Exponentially Weighted Moving Average) volatility
        
        More weight on recent observations
        
        sigma^2[t] = lambda * sigma^2[t-1] + (1-lambda) * r^2[t-1]
        
        RiskMetrics uses lambda = 0.94 for daily data
        
        Args:
            returns: Return series
            lambda_param: Decay parameter (0 < lambda < 1)
            
        Returns:
            VolatilityResult
        """
        logger.info(f"Calculating EWMA volatility (lambda={lambda_param})...")
        
        # Remove NaN
        returns_clean = returns.dropna()
        
        # Calculate EWMA variance
        ewma_var = returns_clean.ewm(alpha=1-lambda_param, adjust=False).var()
        
        # Convert to volatility
        ewma_vol = np.sqrt(ewma_var)
        
        # Current volatility
        current_vol = ewma_vol.iloc[-1]
        
        # Annualize
        annualized_vol = current_vol * np.sqrt(self.periods_per_year)
        
        result = VolatilityResult(
            current_vol=current_vol,
            annualized_vol=annualized_vol,
            vol_series=ewma_vol,
            method='EWMA',
            timestamp=datetime.now(),
            metadata={
                'lambda': lambda_param,
                'half_life': -np.log(2) / np.log(lambda_param)
            }
        )
        
        logger.debug(f"EWMA vol: {current_vol:.4%} (annualized: {annualized_vol:.4%})")
        
        return result
    
    def calculate_rolling(self,
                         returns: pd.Series,
                         window: int = 60) -> VolatilityResult:
        """
        Calculate rolling window volatility
        
        Simple moving standard deviation
        
        Args:
            returns: Return series
            window: Rolling window size
            
        Returns:
            VolatilityResult
        """
        logger.info(f"Calculating rolling volatility (window={window})...")
        
        # Remove NaN
        returns_clean = returns.dropna()
        
        # Calculate rolling std
        rolling_vol = returns_clean.rolling(window=window).std()
        
        # Current volatility
        current_vol = rolling_vol.iloc[-1]
        
        # Annualize
        annualized_vol = current_vol * np.sqrt(self.periods_per_year)
        
        result = VolatilityResult(
            current_vol=current_vol,
            annualized_vol=annualized_vol,
            vol_series=rolling_vol,
            method='Rolling',
            timestamp=datetime.now(),
            metadata={
                'window': window
            }
        )
        
        logger.debug(f"Rolling vol: {current_vol:.4%} (annualized: {annualized_vol:.4%})")
        
        return result
    
    def calculate_realized(self,
                          returns: pd.Series,
                          lookback: int = 252) -> VolatilityResult:
        """
        Calculate realized volatility
        
        Uses actual historical returns
        
        Args:
            returns: Return series
            lookback: Lookback period
            
        Returns:
            VolatilityResult
        """
        logger.info(f"Calculating realized volatility (lookback={lookback})...")
        
        # Remove NaN
        returns_clean = returns.dropna()
        
        # Use last N returns
        recent_returns = returns_clean.iloc[-lookback:]
        
        # Calculate standard deviation
        realized_vol = recent_returns.std()
        
        # Annualize
        annualized_vol = realized_vol * np.sqrt(self.periods_per_year)
        
        result = VolatilityResult(
            current_vol=realized_vol,
            annualized_vol=annualized_vol,
            vol_series=pd.Series([realized_vol], index=[returns.index[-1]]),
            method='Realized',
            timestamp=datetime.now(),
            metadata={
                'lookback': lookback,
                'mean_return': recent_returns.mean(),
                'skewness': recent_returns.skew(),
                'kurtosis': recent_returns.kurtosis()
            }
        )
        
        logger.debug(f"Realized vol: {realized_vol:.4%} (annualized: {annualized_vol:.4%})")
        
        return result
    
    def calculate_parkinson(self,
                           high: pd.Series,
                           low: pd.Series,
                           window: int = 60) -> VolatilityResult:
        """
        Calculate Parkinson volatility estimator
        
        Uses high-low range, more efficient than close-to-close
        
        sigma² = (1/(4·ln(2))) · E[(ln(H/L))²]
        
        Args:
            high: High price series
            low: Low price series
            window: Rolling window
            
        Returns:
            VolatilityResult
        """
        logger.info(f"Calculating Parkinson volatility (window={window})...")
        
        # Calculate log range
        log_hl = np.log(high / low)
        
        # Parkinson estimator
        parkinson_var = (1 / (4 * np.log(2))) * (log_hl ** 2)
        
        # Rolling mean of variance
        rolling_var = parkinson_var.rolling(window=window).mean()
        
        # Convert to volatility
        parkinson_vol = np.sqrt(rolling_var)
        
        # Current volatility
        current_vol = parkinson_vol.iloc[-1]
        
        # Annualize
        annualized_vol = current_vol * np.sqrt(self.periods_per_year)
        
        result = VolatilityResult(
            current_vol=current_vol,
            annualized_vol=annualized_vol,
            vol_series=parkinson_vol,
            method='Parkinson',
            timestamp=datetime.now(),
            metadata={
                'window': window,
                'efficiency_vs_close': 5.2  # Theoretical efficiency gain
            }
        )
        
        logger.debug(f"Parkinson vol: {current_vol:.4%} (annualized: {annualized_vol:.4%})")
        
        return result
    
    def compare_methods(self,
                       returns: pd.Series,
                       high: pd.Series = None,
                       low: pd.Series = None) -> pd.DataFrame:
        """
        Compare all volatility methods
        
        Args:
            returns: Return series
            high: High price series (optional, for Parkinson)
            low: Low price series (optional, for Parkinson)
            
        Returns:
            DataFrame comparing all methods
        """
        results = []
        
        # GARCH
        try:
            garch_result = self.calculate_garch(returns)
            results.append({
                'Method': 'GARCH(1,1)',
                'Current Vol': garch_result.current_vol,
                'Annualized Vol': garch_result.annualized_vol
            })
        except Exception as e:
            logger.warning(f"GARCH failed: {e}")
        
        # EWMA
        try:
            ewma_result = self.calculate_ewma(returns)
            results.append({
                'Method': 'EWMA',
                'Current Vol': ewma_result.current_vol,
                'Annualized Vol': ewma_result.annualized_vol
            })
        except Exception as e:
            logger.warning(f"EWMA failed: {e}")
        
        # Rolling
        try:
            rolling_result = self.calculate_rolling(returns)
            results.append({
                'Method': 'Rolling',
                'Current Vol': rolling_result.current_vol,
                'Annualized Vol': rolling_result.annualized_vol
            })
        except Exception as e:
            logger.warning(f"Rolling failed: {e}")
        
        # Realized
        try:
            realized_result = self.calculate_realized(returns)
            results.append({
                'Method': 'Realized',
                'Current Vol': realized_result.current_vol,
                'Annualized Vol': realized_result.annualized_vol
            })
        except Exception as e:
            logger.warning(f"Realized failed: {e}")
        
        # Parkinson (if high/low provided)
        if high is not None and low is not None:
            try:
                parkinson_result = self.calculate_parkinson(high, low)
                results.append({
                    'Method': 'Parkinson',
                    'Current Vol': parkinson_result.current_vol,
                    'Annualized Vol': parkinson_result.annualized_vol
                })
            except Exception as e:
                logger.warning(f"Parkinson failed: {e}")
        
        return pd.DataFrame(results)
    
    def __repr__(self):
        return f"VolatilityModel(periods_per_year={self.periods_per_year})"


# Convenience functions
def quick_garch(returns: pd.Series) -> float:
    """Quick GARCH volatility calculation"""
    model = VolatilityModel()
    result = model.calculate_garch(returns)
    return result.current_vol


def quick_ewma(returns: pd.Series) -> float:
    """Quick EWMA volatility calculation"""
    model = VolatilityModel()
    result = model.calculate_ewma(returns)
    return result.current_vol
