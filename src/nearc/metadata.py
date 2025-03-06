#!/usr/bin/env python3
"""
Contract metadata handling for the NEAR Python contract compiler.
"""

import json
from pathlib import Path
from typing import Dict, Any
import tomllib

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

    # Initialize metadata with NEP-330 standard
    metadata = {"standards": [{"standard": "nep330", "version": "1.0.0"}]}

    # Extract metadata from pyproject.toml if it exists
    pyproject_path = contract_path.parent / "pyproject.toml"
    if pyproject_path.exists():
        try:
            metadata = extract_metadata_from_pyproject(pyproject_path, metadata)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not read metadata from pyproject.toml: {e}"
            )

    # Get Git information for the contract
    from .reproducible import get_git_info

    git_info = get_git_info(contract_path.parent)

    # Add Git information directly to metadata
    if git_info:
        if "repository" in git_info and "commit" in git_info:
            if "build_info" not in metadata:
                metadata["build_info"] = {}  # type: ignore

            metadata["build_info"]["source_code_snapshot"] = (  # type: ignore
                f"git+{git_info['repository']}#{git_info['commit']}"
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


def extract_metadata_from_pyproject(
    pyproject_path: Path, base_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract metadata from pyproject.toml using standard fields when possible.

    Args:
        pyproject_path: Path to the pyproject.toml file
        base_metadata: Initial metadata dictionary to extend

    Returns:
        Dict containing the updated metadata
    """
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    # Try to get metadata from project section (PEP 621 standard)
    project_data = pyproject_data.get("project", {})

    # Try to get NEAR-specific metadata from tool section
    near_data = pyproject_data.get("tool", {}).get("near", {}).get("contract", {})

    # Get reproducible build data if available
    reproducible_build = (
        pyproject_data.get("tool", {}).get("near", {}).get("reproducible_build", {})
    )

    # Map standard pyproject.toml fields to NEP-330 metadata
    if "version" in project_data:
        base_metadata["version"] = project_data["version"]
    elif "version" in near_data:
        base_metadata["version"] = near_data["version"]

    # Use standard URL field if available, fall back to NEAR-specific link
    if "urls" in project_data and "repository" in project_data["urls"]:
        base_metadata["link"] = project_data["urls"]["repository"]
    elif "url" in project_data:
        base_metadata["link"] = project_data["url"]
    elif "repository" in project_data:
        base_metadata["link"] = project_data["repository"]
    elif "link" in near_data:
        base_metadata["link"] = near_data["link"]

    # Use git repository if available from reproducible build info
    git_info = near_data.get("git_info", {})
    if git_info and "repository" in git_info and not base_metadata.get("link"):
        base_metadata["link"] = git_info["repository"]

    # Handle standards field
    if "standards" in near_data:
        standards = list(
            near_data["standards"]
        )  # Create a new list to avoid modifying the original

        # Ensure NEP-330 is included
        if not any(std.get("standard") == "nep330" for std in standards):
            standards.append({"standard": "nep330", "version": "1.0.0"})

        base_metadata["standards"] = standards

    # Handle build info
    if "build_info" in near_data:
        base_metadata["build_info"] = near_data["build_info"]

    # Add reproducible build information if available
    if reproducible_build:
        base_metadata["build_info"] = {
            "build_environment": reproducible_build.get("image", ""),
            "build_command": reproducible_build.get("container_build_command", []),
        }

        # Add git info if available
        if git_info:
            base_metadata["build_info"]["source_code_snapshot"] = (
                f"git+{git_info.get('repository', '')}#{git_info.get('commit', '')}"
            )

    return base_metadata
