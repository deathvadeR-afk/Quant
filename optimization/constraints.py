"""
Constraint Module for Portfolio Optimization.

This module provides constraint classes for portfolio optimization:
- SectorConstraint: Limits exposure to specific sectors
- PositionSizeConstraint: Limits min/max position sizes
- TurnoverConstraint: Limits portfolio turnover
- GrossExposureConstraint: Limits total exposure
- LongShortRatioConstraint: Limits long/short ratio
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class SectorConstraint:
    """Constraint on sector exposure.
    
    Attributes:
        sector_name: Name of the sector
        max_exposure: Maximum exposure to the sector (as fraction)
    """
    sector_name: str
    max_exposure: float


@dataclass
class PositionSizeConstraint:
    """Constraint on individual position sizes.
    
    Attributes:
        min_weight: Minimum weight for any position
        max_weight: Maximum weight for any position
    """
    min_weight: float
    max_weight: float


@dataclass
class TurnoverConstraint:
    """Constraint on portfolio turnover.
    
    Attributes:
        max_turnover: Maximum turnover (as fraction of portfolio)
    """
    max_turnover: float


@dataclass
class GrossExposureConstraint:
    """Constraint on gross exposure.
    
    Attributes:
        max_exposure: Maximum gross exposure (e.g., 2.0 = 200%)
    """
    max_exposure: float


@dataclass
class LongShortRatioConstraint:
    """Constraint on long/short ratio.
    
    Attributes:
        max_ratio: Maximum ratio of long to short exposure (e.g., 1.3 = 130/30)
    """
    max_ratio: float


class ConstraintBuilder:
    """Builder for portfolio optimization constraints.
    
    This class provides a fluent interface for building constraints.
    
    Usage:
        builder = ConstraintBuilder()
        builder.add_sector_limit("tech", 0.25)
        builder.add_position_size(min_weight=0.01, max_weight=0.10)
        constraints = builder.build()
    """
    
    def __init__(self):
        """Initialize the constraint builder."""
        self.constraints: List[Any] = []
        
    def add_sector_limit(self, sector_name: str, max_exposure: float) -> "ConstraintBuilder":
        """Add a sector exposure limit.
        
        Args:
            sector_name: Name of the sector
            max_exposure: Maximum exposure (e.g., 0.25 for 25%)
            
        Returns:
            Self for method chaining
        """
        self.constraints.append(
            SectorConstraint(sector_name=sector_name, max_exposure=max_exposure)
        )
        return self
        
    def add_position_size(
        self,
        min_weight: Optional[float] = None,
        max_weight: Optional[float] = None
    ) -> "ConstraintBuilder":
        """Add position size constraints.
        
        Args:
            min_weight: Minimum weight for any position
            max_weight: Maximum weight for any position
            
        Returns:
            Self for method chaining
        """
        self.constraints.append(
            PositionSizeConstraint(
                min_weight=min_weight if min_weight is not None else 0.0,
                max_weight=max_weight if max_weight is not None else 1.0
            )
        )
        return self
        
    def add_turnover_limit(self, max_turnover: float) -> "ConstraintBuilder":
        """Add a turnover limit.
        
        Args:
            max_turnover: Maximum turnover (e.g., 0.20 for 20%)
            
        Returns:
            Self for method chaining
        """
        self.constraints.append(
            TurnoverConstraint(max_turnover=max_turnover)
        )
        return self
        
    def add_gross_exposure_limit(self, max_exposure: float) -> "ConstraintBuilder":
        """Add a gross exposure limit.
        
        Args:
            max_exposure: Maximum gross exposure (e.g., 2.0 for 200%)
            
        Returns:
            Self for method chaining
        """
        self.constraints.append(
            GrossExposureConstraint(max_exposure=max_exposure)
        )
        return self
        
    def add_long_short_ratio(self, max_ratio: float) -> "ConstraintBuilder":
        """Add a long/short ratio constraint.
        
        Args:
            max_ratio: Maximum ratio (e.g., 1.3 for 130/30)
            
        Returns:
            Self for method chaining
        """
        self.constraints.append(
            LongShortRatioConstraint(max_ratio=max_ratio)
        )
        return self
        
    def clear(self) -> "ConstraintBuilder":
        """Clear all constraints.
        
        Returns:
            Self for method chaining
        """
        self.constraints = []
        return self
        
    def build(self) -> List[Any]:
        """Build and return the constraint list.
        
        Returns:
            List of constraint objects
        """
        return self.constraints
        
    def __len__(self) -> int:
        """Return number of constraints."""
        return len(self.constraints)
        
    def __iter__(self):
        """Iterate over constraints."""
        return iter(self.constraints)
        
    def __getitem__(self, index: int) -> Any:
        """Get constraint by index."""
        return self.constraints[index]


def validate_constraints(
    weights: np.ndarray,
    tickers: List[str],
    sector_mapping: Dict[str, str],
    constraints: List[Any]
) -> Dict[str, Any]:
    """Validate that weights satisfy all constraints.
    
    Args:
        weights: Portfolio weights
        tickers: List of ticker symbols
        sector_mapping: Dict mapping ticker to sector
        constraints: List of constraint objects
        
    Returns:
        Dict with 'valid' boolean and 'violations' list
    """
    violations = []
    
    for constraint in constraints:
        if isinstance(constraint, PositionSizeConstraint):
            for i, w in enumerate(weights):
                if w < constraint.min_weight - 1e-6:
                    violations.append(
                        f"Position {tickers[i]}: weight {w:.4f} < min {constraint.min_weight:.4f}"
                    )
                if w > constraint.max_weight + 1e-6:
                    violations.append(
                        f"Position {tickers[i]}: weight {w:.4f} > max {constraint.max_weight:.4f}"
                    )
                    
        elif isinstance(constraint, SectorConstraint):
            sector_weights = {}
            for i, ticker in enumerate(tickers):
                sector = sector_mapping.get(ticker, "unknown")
                if sector not in sector_weights:
                    sector_weights[sector] = 0.0
                sector_weights[sector] += weights[i]
                
            if constraint.sector_name in sector_weights:
                if sector_weights[constraint.sector_name] > constraint.max_exposure + 1e-6:
                    violations.append(
                        f"Sector {constraint.sector_name}: exposure "
                        f"{sector_weights[constraint.sector_name]:.4f} > max {constraint.max_exposure:.4f}"
                    )
                    
        elif isinstance(constraint, GrossExposureConstraint):
            gross_exposure = np.sum(np.abs(weights))
            if gross_exposure > constraint.max_exposure + 1e-6:
                violations.append(
                    f"Gross exposure: {gross_exposure:.4f} > max {constraint.max_exposure:.4f}"
                )
                
        elif isinstance(constraint, LongShortRatioConstraint):
            long_exposure = np.sum(weights[weights > 0])
            short_exposure = np.sum(np.abs(weights[weights < 0]))
            if short_exposure > 0:
                ratio = long_exposure / short_exposure
                if ratio > constraint.max_ratio + 1e-6:
                    violations.append(
                        f"Long/short ratio: {ratio:.4f} > max {constraint.max_ratio:.4f}"
                    )
                    
    return {
        "valid": len(violations) == 0,
        "violations": violations
    }