#!/usr/bin/env python3
"""
Contract metadata handling for the NEAR Python contract compiler.
"""

import json
import tomllib
from pathlib import Path

from .utils import console


def inject_metadata_function(contract_path: Path) -> Path:
    """
    Inject the contract_source_metadata function into a contract if it doesn't exist.

    Args:
        contract_path: Path to the contract file

    Returns:
        Path to the possibly modified contract file
    """
    # First check if the function already exists
    with open(contract_path) as f:
        content = f.read()

    if "def contract_source_metadata()" in content:
        return contract_path  # No injection needed

    # Try to extract metadata from pyproject.toml if it exists
    metadata = {"standards": [{"standard": "nep330", "version": "1.0.0"}]}

    pyproject_path = contract_path.parent / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)

            # Extract metadata from pyproject.toml
            contract_info = (
                pyproject_data.get("tool", {}).get("near", {}).get("contract", {})
            )

            if "version" in contract_info:
                metadata["version"] = contract_info["version"]
            if "link" in contract_info:
                metadata["link"] = contract_info["link"]
            if "standards" in contract_info:
                # Merge with existing standards, ensuring nep330 is included
                standards = contract_info["standards"]
                has_nep330 = False
                for std in standards:
                    if std.get("standard") == "nep330":
                        has_nep330 = True
                        break

                if not has_nep330:
                    standards.append({"standard": "nep330", "version": "1.0.0"})

                metadata["standards"] = standards

            if "build_info" in contract_info:
                metadata["build_info"] = contract_info["build_info"]
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not read metadata from pyproject.toml: {e}"
            )

    # Create the function code
    metadata_code = f"""

# Auto-generated NEP-330 metadata function
import near

@near.export
def contract_source_metadata():
    near.value_return('{json.dumps(metadata)}')
"""

    # Create a modified file with the appended function
    modified_path = contract_path.parent / f"{contract_path.stem}_with_metadata.py"
    with open(modified_path, "w") as f:
        f.write(content)
        f.write(metadata_code)

    console.print("[cyan]Added NEP-330 metadata function to contract[/]")

    return modified_path
