#!/usr/bin/env python3
"""
Contract metadata handling for the NEAR Python contract compiler.
"""

import json
from pathlib import Path
from near_abi_py import generate_abi
import zstd

from .utils import console


def inject_abi(contract_path: Path) -> Path:
    """
    Inject the ABI function into a contract

    Args:
        contract_path: Path to the contract file

    Returns:
        Path to the possibly modified contract file
    """
    # First check if the function already exists
    with open(contract_path) as f:
        content = f.read()

    package_path = None
    pyproject_path = contract_path.parent / "pyproject.toml"
    if pyproject_path.exists():
        package_path = pyproject_path

    abi = generate_abi(contract_file=str(contract_path), package_path=str(package_path))
    compressed_abi = zstd.compress(json.dumps(abi).encode())

    # Convert the bytes to a proper Python bytes literal
    bytes_repr = repr(compressed_abi)

    # Create the function code that returns the literal bytes object
    abi_code = f"""
# Auto-generated ABI function
import near

@near.export
def __contract_abi():
    near.value_return({bytes_repr})

"""

    # Create a modified file with the appended function
    modified_path = contract_path.parent / f"{contract_path.stem}_with_abi.py"
    with open(modified_path, "w") as f:
        f.write(content)
        f.write(abi_code)

    console.print("[cyan]Added ABI to contract[/]")
    return modified_path
