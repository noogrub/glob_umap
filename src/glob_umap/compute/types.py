from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

@dataclass(frozen=True, order=True)
class StableKey:
    """Stable identity for one source-catalogue record."""
    catalog_code: str
    source_file: str
    source_row: int

@dataclass(frozen=True)
class MatrixData:
    """Numerical feature matrix and corresponding object identities"""
    object_ids:    NDArray[np.int64]      # 1D integer array
    stable_keys:   tuple[StableKey, ...]  # One key per matrix row (catalog_code, source_file, source_row)
    labels:        NDArray[np.str_]       # 1D class label array
    values:        NDArray[np.float64]    # 2D numerical matrix 
    feature_names: tuple[str, ...]        # One ordered name per matrix column
