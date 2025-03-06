"""
NEARC - NEAR Python Contract Compiler

This package provides tools to compile Python smart contracts to WebAssembly
for deployment on the NEAR blockchain.
"""

from .cli import main

__version__ = "0.3.3"

__all__ = ["main"]
