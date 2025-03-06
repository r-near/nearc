#!/usr/bin/env python3
"""
Reproducible builds module for the NEAR Python contract compiler.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List
import tomllib
import tomli_w

from .utils import console, run_command_with_progress


def get_git_info(contract_dir: Path) -> Dict[str, Any]:
    """
    Get Git repository information for the contract.

    Args:
        contract_dir: Path to the contract directory

    Returns:
        Dictionary with Git information or empty dict if not a Git repo
    """
    git_info: dict = {}

    try:
        # Check if in git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=contract_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return git_info

        # Get remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=contract_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            git_info["repository"] = result.stdout.strip()

        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=contract_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            git_info["commit"] = result.stdout.strip()

        # Check if working tree is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=contract_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        git_info["clean"] = result.stdout.strip() == ""

        return git_info
    except Exception as e:
        console.print(f"[yellow]Warning: Error getting Git info: {e}")
        return {}


def verify_git_status(contract_dir: Path) -> bool:
    """
    Verify that the Git repository is clean and has a remote.

    Args:
        contract_dir: Path to the contract directory

    Returns:
        True if the repository is clean and has a remote, False otherwise
    """
    git_info = get_git_info(contract_dir)

    if not git_info:
        console.print("[red]Error: Not a Git repository")
        return False

    if not git_info.get("repository"):
        console.print("[red]Error: Git repository has no remote URL")
        return False

    if not git_info.get("clean", False):
        console.print(
            "[red]Error: Git working tree is not clean. Please commit all changes."
        )
        return False

    return True


def read_reproducible_build_config(contract_dir: Path) -> Dict[str, Any]:
    """
    Read reproducible build configuration from pyproject.toml.

    Args:
        contract_dir: Path to the contract directory

    Returns:
        Dictionary with reproducible build configuration
    """
    pyproject_path = contract_dir / "pyproject.toml"

    if not pyproject_path.exists():
        console.print("[red]Error: No pyproject.toml found")
        return {}

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Check for reproducible build configuration
        reproducible_build = (
            pyproject_data.get("tool", {}).get("near", {}).get("reproducible_build", {})
        )

        if not reproducible_build:
            console.print(
                "[yellow]Warning: No reproducible build configuration found in pyproject.toml"
            )
            console.print(
                "[yellow]Add [tool.near.reproducible_build] section with image, image_digest, and container_build_command"
            )

        return reproducible_build
    except Exception as e:
        console.print(f"[red]Error reading pyproject.toml: {e}")
        return {}


def run_reproducible_build(
    contract_path: Path, output_path: Path, build_args: List[str]
) -> bool:
    """
    Run a reproducible build in a Docker container.

    Args:
        contract_path: Path to the contract file
        output_path: Path to the output WASM file
        build_args: Arguments for the build command

    Returns:
        True if successful, False otherwise
    """
    contract_dir = contract_path.parent

    # Verify Git status
    if not verify_git_status(contract_dir):
        return False

    # Read reproducible build configuration
    config = read_reproducible_build_config(contract_dir)

    if not config:
        return False

    # Check required configuration
    required_fields = ["image", "image_digest", "container_build_command"]
    for field in required_fields:
        if field not in config:
            console.print(
                f"[red]Error: Missing '{field}' in reproducible build configuration"
            )
            return False

    # Extract configuration
    image = config["image"]
    image_digest = config["image_digest"]
    container_build_command = config["container_build_command"]

    # Construct Docker image with digest
    docker_image = f"{image}@{image_digest}"

    # Get absolute paths
    abs_contract_dir = contract_dir.resolve()
    rel_contract_path = contract_path.name
    rel_output_path = output_path.name

    # Add additional build args if provided
    build_command = container_build_command + [rel_contract_path] + build_args
    if "--output" not in " ".join(build_command) and "-o" not in " ".join(
        build_command
    ):
        build_command.extend(["-o", rel_output_path])

    # Run Docker container
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{abs_contract_dir}:/build",
        "-w",
        "/build",
        "--entrypoint",
        "/bin/sh",
        docker_image,
        "-c",
        " ".join(build_command),
    ]

    console.print(
        f"[cyan]Running reproducible build in Docker container: {docker_image}"
    )
    console.print(f"[cyan]Build command: {' '.join(build_command)}")

    if not run_command_with_progress(docker_cmd, cwd=contract_dir):
        console.print("[red]Failed to run reproducible build in Docker container")
        return False

    if not output_path.exists():
        console.print(f"[red]Error: Output file {output_path} was not created")
        return False

    # Show success message with file size
    size_kb = output_path.stat().st_size / 1024
    console.print(
        f"[bold green]Successfully built reproducible contract:[/] [cyan]{output_path}[/] [yellow]({size_kb:.1f} KB)[/]"
    )

    return True


def init_reproducible_build_config(contract_dir: Path) -> bool:
    """
    Initialize reproducible build configuration in pyproject.toml.

    Args:
        contract_dir: Path to the contract directory

    Returns:
        True if successful, False otherwise
    """
    pyproject_path = contract_dir / "pyproject.toml"

    if not pyproject_path.exists():
        # Create a new pyproject.toml file
        with open(pyproject_path, "w") as f:
            f.write("[project]\n")
            f.write('name = "near-contract"\n')
            f.write('version = "0.1.0"\n')
            f.write('requires-python = ">=3.11"\n\n')

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Ensure tool.near section exists
        if "tool" not in pyproject_data:
            pyproject_data["tool"] = {}
        if "near" not in pyproject_data["tool"]:
            pyproject_data["tool"]["near"] = {}

        # Add reproducible build configuration
        pyproject_data["tool"]["near"]["reproducible_build"] = {
            "image": "ghcr.io/r-near/nearc:main",
            "image_digest": "sha256:REPLACE_THIS_WITH_ACTUAL_DIGEST",
            "container_build_command": ["nearc"],
        }

        # Write updated pyproject.toml
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(pyproject_data, f)

        console.print(
            "[green]Initialized reproducible build configuration in pyproject.toml"
        )
        console.print(
            "[yellow]Please update the image_digest with the actual digest of the Docker image"
        )

        return True
    except Exception as e:
        console.print(f"[red]Error updating pyproject.toml: {e}")
        return False
