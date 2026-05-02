"""
Factor Calculator Module.

This module provides factor calculation classes for:
- Value factors (P/E, P/B, EV/EBITDA, dividend yield, price/FCF)
- Momentum factors (1M, 3M, 6M, 12M returns, RSI, MACD)
- Quality factors (ROE, ROA, profit margin, debt/equity, earnings stability)
- Volatility factors (20d historical vol, beta, max drawdown)
- Size factor (market cap percentile)

All calculations are designed to be vectorized for performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Union
from datetime import date, datetime


class ValueFactors:
    """Calculate value factors."""
    
    def calculate_pe_ratio(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate P/E ratio for each ticker.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and P/E values
        """
        pe_data = fundamental_data[fundamental_data['metric'] == 'pe_ratio']
        if pe_data.empty:
            return pd.Series(dtype=float)
        
        return pe_data.groupby('ticker')['value'].last()
    
    def calculate_pb_ratio(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate P/B ratio for each ticker.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and P/B values
        """
        pb_data = fundamental_data[fundamental_data['metric'] == 'pb_ratio']
        if pb_data.empty:
            return pd.Series(dtype=float)
        
        return pb_data.groupby('ticker')['value'].last()
    
    def calculate_ev_ebitda(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate EV/EBITDA ratio for each ticker.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and EV/EBITDA values
        """
        ev_data = fundamental_data[fundamental_data['metric'] == 'enterprise_value']
        ebitda_data = fundamental_data[fundamental_data['metric'] == 'ebitda']
        
        if ev_data.empty or ebitda_data.empty:
            return pd.Series(dtype=float)
        
        ev = ev_data.groupby('ticker')['value'].last()
        ebitda = ebitda_data.groupby('ticker')['value'].last()
        
        # Calculate EV/EBITDA, handling division by zero
        result = pd.Series(index=ev.index, dtype=float)
        for ticker in ev.index:
            if ticker in ebitda.index and ebitda[ticker] > 0:
                result[ticker] = ev[ticker] / ebitda[ticker]
            else:
                result[ticker] = np.nan
        
        return result
    
    def _get_enterprise_value(self, ticker: str) -> float:
        """Get enterprise value for a ticker."""
        return 0.0
    
    def _get_ebitda(self, ticker: str) -> float:
        """Get EBITDA for a ticker."""
        return 0.0
    
    def calculate_dividend_yield(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate dividend yield for each ticker.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and dividend yield values
        """
        dy_data = fundamental_data[fundamental_data['metric'] == 'dividend_yield']
        if dy_data.empty:
            return pd.Series(dtype=float)
        
        return dy_data.groupby('ticker')['value'].last()
    
    def calculate_price_to_fcf(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate Price to Free Cash Flow ratio.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and Price/FCF values
        """
        price_data = fundamental_data[fundamental_data['metric'] == 'price']
        fcf_data = fundamental_data[fundamental_data['metric'] == 'free_cash_flow']
        
        if price_data.empty or fcf_data.empty:
            return pd.Series(dtype=float)
        
        price = price_data.groupby('ticker')['value'].last()
        fcf = fcf_data.groupby('ticker')['value'].last()
        
        result = pd.Series(index=price.index, dtype=float)
        for ticker in price.index:
            if ticker in fcf.index and fcf[ticker] > 0:
                result[ticker] = price[ticker] / fcf[ticker]
            else:
                result[ticker] = np.nan
        
        return result


class MomentumFactors:
    """Calculate momentum factors."""
    
    def calculate_cumulative_return(
        self, 
        price_data: pd.DataFrame, 
        window_days: int = 21
    ) -> pd.Series:
        """
        Calculate cumulative return over specified window.
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            window_days: Number of days for the return calculation
            
        Returns:
            Series with ticker index and cumulative return values
        """
        if price_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < 2:
                results[ticker] = np.nan
                continue
            
            # Get the most recent price and price N days ago
            prices = ticker_data['close'].values
            if len(prices) >= window_days:
                start_price = prices[-window_days]
                end_price = prices[-1]
            else:
                start_price = prices[0]
                end_price = prices[-1]
            
            if start_price > 0:
                results[ticker] = (end_price - start_price) / start_price
            else:
                results[ticker] = np.nan
        
        return pd.Series(results)
    
    def calculate_rsi(
        self, 
        price_data: pd.DataFrame, 
        window: int = 14
    ) -> pd.Series:
        """
        Calculate RSI(14).
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            window: RSI window (default 14)
            
        Returns:
            Series with ticker index and RSI values (0-100)
        """
        if price_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < window + 1:
                results[ticker] = np.nan
                continue
            
            prices = ticker_data['close'].values
            
            # Calculate price changes
            deltas = np.diff(prices)
            
            # Separate gains and losses
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calculate average gains and losses
            avg_gain = np.mean(gains[-window:])
            avg_loss = np.mean(losses[-window:])
            
            if avg_loss == 0:
                results[ticker] = 100
            else:
                rs = avg_gain / avg_loss
                results[ticker] = 100 - (100 / (1 + rs))
        
        return pd.Series(results)
    
    def calculate_macd(
        self, 
        price_data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> pd.Series:
        """
        Calculate MACD histogram.
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            
        Returns:
            Series with ticker index and MACD histogram values
        """
        if price_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < slow_period + signal_period:
                results[ticker] = np.nan
                continue
            
            prices = ticker_data['close'].values
            
            # Calculate EMAs
            ema_fast = self._calculate_ema(prices, fast_period)
            ema_slow = self._calculate_ema(prices, slow_period)
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line (EMA of MACD)
            signal_line = self._calculate_ema(macd_line, signal_period)
            
            # MACD histogram
            results[ticker] = macd_line[-1] - signal_line[-1]
        
        return pd.Series(results)
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.array([np.nan] * len(prices))
        
        ema = np.zeros(len(prices))
        ema[:period] = np.nan
        
        # First EMA is SMA
        ema[period - 1] = np.mean(prices[:period])
        
        # Multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate EMA
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        return ema


class QualityFactors:
    """Calculate quality factors."""
    
    def calculate_roe(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate Return on Equity (ROE).
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and ROE values
        """
        roe_data = fundamental_data[fundamental_data['metric'] == 'roe']
        if roe_data.empty:
            return pd.Series(dtype=float)
        
        return roe_data.groupby('ticker')['value'].last()
    
    def calculate_roa(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate Return on Assets (ROA).
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and ROA values
        """
        roa_data = fundamental_data[fundamental_data['metric'] == 'roa']
        if roa_data.empty:
            return pd.Series(dtype=float)
        
        return roa_data.groupby('ticker')['value'].last()
    
    def calculate_profit_margin(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate profit margin.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and profit margin values
        """
        pm_data = fundamental_data[fundamental_data['metric'] == 'profit_margin']
        if pm_data.empty:
            return pd.Series(dtype=float)
        
        return pm_data.groupby('ticker')['value'].last()
    
    def calculate_debt_equity(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate debt/equity ratio.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and debt/equity values
        """
        de_data = fundamental_data[fundamental_data['metric'] == 'debt_equity']
        if de_data.empty:
            return pd.Series(dtype=float)
        
        return de_data.groupby('ticker')['value'].last()
    
    def calculate_earnings_stability(self, fundamental_data: pd.DataFrame) -> pd.Series:
        """
        Calculate earnings stability (inverse of earnings volatility).
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and earnings stability values
        """
        # For now, return a simple implementation
        # In production, this would calculate the coefficient of variation of earnings
        earnings_data = fundamental_data[fundamental_data['metric'] == 'earnings']
        if earnings_data.empty:
            return pd.Series(dtype=float)
        
        # Group by ticker and calculate stability
        stability = {}
        for ticker in earnings_data['ticker'].unique():
            ticker_data = earnings_data[earnings_data['ticker'] == ticker]['value']
            if len(ticker_data) > 1 and ticker_data.std() > 0:
                # Lower coefficient of variation = higher stability
                cv = ticker_data.std() / abs(ticker_data.mean())
                stability[ticker] = 1 / (1 + cv)  # Normalize to 0-1
            else:
                stability[ticker] = np.nan
        
        return pd.Series(stability)


class VolatilityFactors:
    """Calculate volatility factors."""
    
    def calculate_historical_volatility(
        self, 
        price_data: pd.DataFrame, 
        window_days: int = 20
    ) -> pd.Series:
        """
        Calculate historical volatility.
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            window_days: Window for volatility calculation (default 20)
            
        Returns:
            Series with ticker index and volatility values
        """
        if price_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < window_days + 1:
                results[ticker] = np.nan
                continue
            
            prices = ticker_data['close'].values
            
            # Calculate daily returns
            returns = np.diff(prices) / prices[:-1]
            
            # Get the most recent window
            recent_returns = returns[-window_days:]
            
            # Annualized volatility
            results[ticker] = np.std(recent_returns) * np.sqrt(252)
        
        return pd.Series(results)
    
    def calculate_beta(
        self, 
        price_data: pd.DataFrame, 
        market_data: pd.DataFrame,
        window_days: int = 60
    ) -> pd.Series:
        """
        Calculate beta against market.
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            market_data: DataFrame with market (e.g., SPY) price data
            window_days: Window for beta calculation (default 60)
            
        Returns:
            Series with ticker index and beta values
        """
        if price_data.empty or market_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        
        # Get market returns
        market_ticker_data = market_data[market_data['ticker'] == 'SPY'].sort_values('date')
        if len(market_ticker_data) < window_days + 1:
            return pd.Series(dtype=float)
        
        market_prices = market_ticker_data['close'].values
        market_returns = np.diff(market_prices) / market_prices[:-1]
        market_returns = market_returns[-window_days:]
        
        market_variance = np.var(market_returns)
        
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < window_days + 1:
                results[ticker] = np.nan
                continue
            
            prices = ticker_data['close'].values
            stock_returns = np.diff(prices) / prices[:-1]
            stock_returns = stock_returns[-window_days:]
            
            # Calculate covariance
            covariance = np.cov(stock_returns, market_returns)[0, 1]
            
            if market_variance > 0:
                results[ticker] = covariance / market_variance
            else:
                results[ticker] = np.nan
        
        return pd.Series(results)
    
    def calculate_max_drawdown(
        self, 
        price_data: pd.DataFrame, 
        window_days: int = 252
    ) -> pd.Series:
        """
        Calculate maximum drawdown.
        
        Args:
            price_data: DataFrame with columns [ticker, date, close, ...]
            window_days: Window for drawdown calculation (default 252 = 1 year)
            
        Returns:
            Series with ticker index and max drawdown values (negative)
        """
        if price_data.empty:
            return pd.Series(dtype=float)
        
        results = {}
        for ticker in price_data['ticker'].unique():
            ticker_data = price_data[price_data['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < 2:
                results[ticker] = np.nan
                continue
            
            prices = ticker_data['close'].values
            
            # Get the most recent window
            if len(prices) > window_days:
                prices = prices[-window_days:]
            
            # Calculate running maximum
            running_max = np.maximum.accumulate(prices)
            
            # Calculate drawdown
            drawdown = (prices - running_max) / running_max
            
            # Maximum drawdown (most negative value)
            results[ticker] = np.min(drawdown)
        
        return pd.Series(results)


class SizeFactor:
    """Calculate size factor."""
    
    def calculate_market_cap_percentile(
        self, 
        fundamental_data: pd.DataFrame
    ) -> pd.Series:
        """
        Calculate market cap percentile within universe.
        
        Args:
            fundamental_data: DataFrame with columns [ticker, report_date, metric, value]
            
        Returns:
            Series with ticker index and market cap percentile (0-1)
        """
        mc_data = fundamental_data[fundamental_data['metric'] == 'market_cap']
        if mc_data.empty:
            return pd.Series(dtype=float)
        
        market_caps = mc_data.groupby('ticker')['value'].last()
        
        # Calculate percentile rank
        percentile = market_caps.rank(pct=True)
        
        return percentile