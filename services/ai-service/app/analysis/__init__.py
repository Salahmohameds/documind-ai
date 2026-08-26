"""Deterministic local analysis engines (classification, extraction, risk).

These run identically on every backend. They are what makes AI_BACKEND=mock a
real implementation rather than a stub, and they are the graceful-degradation
path when a live provider is unreachable.
"""
