"""
Factor Library Module.

This module provides a registry of all available factors with their metadata:
- Factor name and category
- Calculation method
- Interpretation guide
- Calculation frequency

The library contains 20+ factors across 5 categories:
- Value: P/E, P/B, EV/EBITDA, dividend yield, price/FCF
- Momentum: 1M, 3M, 6M, 12M returns, RSI(14), MACD histogram
- Quality: ROE, ROA, profit margin, debt/equity, earnings stability
- Volatility: 20d historical vol, beta, max drawdown
- Size: market cap percentile
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FactorMetadata:
    """Metadata for a single factor."""
    name: str
    category: str
    description: str
    formula: str
    interpretation: str
    calculation_frequency: str
    lower_is_better: bool = False


class FactorLibrary:
    """
    Registry of all available factors with metadata.
    
    This class provides access to factor definitions and metadata
    for the factor analysis engine.
    """
    
    def __init__(self):
        """Initialize the factor library with all factor definitions."""
        self._factors = self._create_factor_definitions()
    
    def _create_factor_definitions(self) -> Dict[str, FactorMetadata]:
        """Create all factor definitions."""
        return {
            # Value Factors
            'pe_ratio': FactorMetadata(
                name='pe_ratio',
                category='value',
                description='Price-to-Earnings ratio',
                formula='Price / Earnings Per Share',
                interpretation='Lower P/E may indicate undervaluation. Higher P/E may indicate growth expectations.',
                calculation_frequency='daily',
                lower_is_better=True
            ),
            'pb_ratio': FactorMetadata(
                name='pb_ratio',
                category='value',
                description='Price-to-Book ratio',
                formula='Price / Book Value Per Share',
                interpretation='Lower P/B may indicate undervaluation relative to book assets.',
                calculation_frequency='daily',
                lower_is_better=True
            ),
            'ev_ebitda': FactorMetadata(
                name='ev_ebitda',
                category='value',
                description='Enterprise Value to EBITDA',
                formula='Enterprise Value / EBITDA',
                interpretation='Lower EV/EBITDA may indicate a cheaper acquisition candidate.',
                calculation_frequency='daily',
                lower_is_better=True
            ),
            'dividend_yield': FactorMetadata(
                name='dividend_yield',
                category='value',
                description='Dividend Yield',
                formula='Annual Dividends / Stock Price',
                interpretation='Higher dividend yield indicates more income return.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'price_to_fcf': FactorMetadata(
                name='price_to_fcf',
                category='value',
                description='Price to Free Cash Flow',
                formula='Price / Free Cash Flow Per Share',
                interpretation='Lower ratio may indicate undervaluation relative to cash generation.',
                calculation_frequency='daily',
                lower_is_better=True
            ),
            
            # Momentum Factors
            'momentum_1m': FactorMetadata(
                name='momentum_1m',
                category='momentum',
                description='1-Month Return',
                formula='(Price_t / Price_{t-21}) - 1',
                interpretation='Higher momentum indicates recent outperformance.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'momentum_3m': FactorMetadata(
                name='momentum_3m',
                category='momentum',
                description='3-Month Return',
                formula='(Price_t / Price_{t-63}) - 1',
                interpretation='Medium-term momentum signal.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'momentum_6m': FactorMetadata(
                name='momentum_6m',
                category='momentum',
                description='6-Month Return',
                formula='(Price_t / Price_{t-126}) - 1',
                interpretation='Medium-to-long term momentum signal.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'momentum_12m': FactorMetadata(
                name='momentum_12m',
                category='momentum',
                description='12-Month Return',
                formula='(Price_t / Price_{t-252}) - 1',
                interpretation='Long-term momentum signal.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'rsi_14': FactorMetadata(
                name='rsi_14',
                category='momentum',
                description='Relative Strength Index (14-day)',
                formula='100 - (100 / (1 + RS)) where RS = Avg Gain / Avg Loss',
                interpretation='RSI > 70 indicates overbought, RSI < 30 indicates oversold.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'macd_histogram': FactorMetadata(
                name='macd_histogram',
                category='momentum',
                description='MACD Histogram',
                formula='MACD Line - Signal Line (EMAs of price)',
                interpretation='Positive histogram indicates bullish momentum.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            
            # Quality Factors
            'roe': FactorMetadata(
                name='roe',
                category='quality',
                description='Return on Equity',
                formula='Net Income / Shareholders Equity',
                interpretation='Higher ROE indicates more efficient use of equity capital.',
                calculation_frequency='quarterly',
                lower_is_better=False
            ),
            'roa': FactorMetadata(
                name='roa',
                category='quality',
                description='Return on Assets',
                formula='Net Income / Total Assets',
                interpretation='Higher ROA indicates more efficient use of all assets.',
                calculation_frequency='quarterly',
                lower_is_better=False
            ),
            'profit_margin': FactorMetadata(
                name='profit_margin',
                category='quality',
                description='Profit Margin',
                formula='Net Income / Revenue',
                interpretation='Higher margin indicates better pricing power and cost control.',
                calculation_frequency='quarterly',
                lower_is_better=False
            ),
            'debt_equity': FactorMetadata(
                name='debt_equity',
                category='quality',
                description='Debt-to-Equity Ratio',
                formula='Total Debt / Shareholders Equity',
                interpretation='Lower D/E indicates less financial leverage risk.',
                calculation_frequency='quarterly',
                lower_is_better=True
            ),
            'earnings_stability': FactorMetadata(
                name='earnings_stability',
                category='quality',
                description='Earnings Stability',
                formula='1 / (1 + CV) where CV = Std(Earnings) / |Mean(Earnings)|',
                interpretation='Higher stability indicates more predictable earnings.',
                calculation_frequency='quarterly',
                lower_is_better=False
            ),
            
            # Volatility Factors
            'historical_volatility_20d': FactorMetadata(
                name='historical_volatility_20d',
                category='volatility',
                description='20-Day Historical Volatility',
                formula='Std(Daily Returns) * sqrt(252)',
                interpretation='Lower volatility indicates more stable price behavior.',
                calculation_frequency='daily',
                lower_is_better=True
            ),
            'beta': FactorMetadata(
                name='beta',
                category='volatility',
                description='Beta (vs SPY)',
                formula='Cov(Stock Returns, Market Returns) / Var(Market Returns)',
                interpretation='Beta > 1 indicates higher market sensitivity.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            'max_drawdown': FactorMetadata(
                name='max_drawdown',
                category='volatility',
                description='Maximum Drawdown (1-year)',
                formula='Min((Price - Running Max) / Running Max)',
                interpretation='Less negative (closer to 0) indicates smaller peak-to-trough decline.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
            
            # Size Factor
            'market_cap_percentile': FactorMetadata(
                name='market_cap_percentile',
                category='size',
                description='Market Cap Percentile',
                formula='Rank(Market Cap) / Total Count',
                interpretation='Higher percentile indicates larger company size.',
                calculation_frequency='daily',
                lower_is_better=False
            ),
        }
    
    def list_all_factors(self) -> List[str]:
        """Get list of all factor names."""
        return list(self._factors.keys())
    
    def get_factors_by_category(self, category: str) -> List[str]:
        """Get all factors in a specific category."""
        return [
            name for name, meta in self._factors.items()
            if meta.category == category
        ]
    
    def get_factor_metadata(self, factor_name: str) -> Optional[Dict]:
        """Get metadata for a specific factor."""
        if factor_name not in self._factors:
            return None
        
        meta = self._factors[factor_name]
        return {
            'name': meta.name,
            'category': meta.category,
            'description': meta.description,
            'formula': meta.formula,
            'interpretation': meta.interpretation,
            'calculation_frequency': meta.calculation_frequency,
            'lower_is_better': meta.lower_is_better
        }
    
    def get_categories(self) -> List[str]:
        """Get all factor categories."""
        return list(set(meta.category for meta in self._factors.values()))
    
    def get_factors_by_frequency(self, frequency: str) -> List[str]:
        """Get all factors with a specific calculation frequency."""
        return [
            name for name, meta in self._factors.items()
            if meta.calculation_frequency == frequency
        ]