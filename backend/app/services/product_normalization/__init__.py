"""Product normalization package.

This package contains the layered product normalization system used
by KVITT to turn messy receipt line labels into stable product
categories and canonical display names.

Layers (in order):

1. Text pre-processing and candidate extraction (Sweden-biased)
2. Deterministic rule engine (hard-coded domain knowledge)
3. Mapping repository (extensible mapping "database")
4. Optional AI-assisted classifier (stubbed for now)

External callers should not depend on individual modules; instead
use :func:`app.services.product_normalization.engine.classify_product`.
"""

from .engine import classify_product  # re-export for convenience

__all__ = ["classify_product"]
