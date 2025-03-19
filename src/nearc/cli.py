#!/usr/bin/env python3
"""
Command-line interface for the NEAR Python contract compiler.
"""

import shutil
import sys
from pathlib import Path
from typing import Optional

import rich_click as click

from .builder import compile_contract
from .utils import console, is_running_in_container, setup_venv


def find_contract_file() -> Optional[Path]:
    """
    Automatically detect a contract file in the current directory.
    Looks for __init__.py first, then main.py.

    Returns:
        Path to the contract file if found, None otherwise
    """
    current_dir = Path.cwd()

    # Check for __init__.py
    init_path = current_dir / "__init__.py"
    if init_path.exists() and init_path.is_file():
        return init_path

    # Check for main.py
    main_path = current_dir / "main.py"
    if main_path.exists() and main_path.is_file():
        return main_path

    # No contract file found
    return None


def check_reproducible_config() -> bool:
    """
    Check if reproducible build configuration exists in the current directory.

    Returns:
        bool: True if configuration exists, False otherwise
    """
    from pathlib import Path

    import tomli

    config_path = Path.cwd() / "pyproject.toml"
    if not config_path.exists():
        return False

    try:
        with open(config_path, "rb") as f:
            config = tomli.load(f)

        # Check if reproducible build configuration exists
        return bool(
            config.get("tool", {}).get("near", {}).get("reproducible_build", {})
        )
    except Exception:
        return False


@click.command()
@click.argument(
    "contract", type=click.Path(exists=True, dir_okay=False), required=False
)
@click.option("--output", "-o", help="Output WASM file path")
@click.option("--venv", help="Path to virtual environment", default=".venv")
@click.option("--rebuild", is_flag=True, help="Force a clean rebuild")
@click.option(
    "--non-reproducible",
    is_flag=True,
    help="Build without reproducibility guarantees (not recommended for production)",
)
@click.option(
    "--init-reproducible-config",
    is_flag=True,
    help="Initialize reproducible build configuration in pyproject.toml",
)
@click.option(
    "--single-file",
    is_flag=True,
    help="Skip local module discovery, compile only the specified file",
)
@click.option(
    "--create-venv",
    is_flag=True,
    help="Force setup of virtual environment before building",
)
def main(
    contract: Optional[str],
    output: Optional[str],
    venv: str,
    rebuild: bool,
    non_reproducible: bool,
    init_reproducible_config: bool,
    single_file: bool,
    create_venv: bool,
):
    """Compile a Python contract to WebAssembly for NEAR blockchain.

    If CONTRACT is not specified, looks for __init__.py or main.py in the current directory.

    By default, builds in reproducible mode for contract verification. Use --non-reproducible
    for faster development builds when verification isn't needed.
    """
    # Handle initialization of reproducible build configuration
    if init_reproducible_config:
        from .reproducible import init_reproducible_build_config

        current_dir = Path.cwd()
        if init_reproducible_build_config(current_dir):
            console.print("[green]Reproducible build configuration initialized")
        else:
            console.print("[red]Failed to initialize reproducible build configuration")
        sys.exit(0)

    # Try to auto-detect contract file if not provided
    contract_path = None
    if contract:
        contract_path = Path(contract).resolve()
    else:
        detected_contract = find_contract_file()
        if detected_contract:
            contract_path = detected_contract.resolve()
            console.print(
                f"[cyan]Auto-detected contract file:[/] [yellow]{contract_path}[/]"
            )
        else:
            console.print(
                "[red]Error: No contract file specified and could not auto-detect __init__.py or main.py"
            )
            console.print(
                "[cyan]Please specify a contract file or create an __init__.py or main.py file"
            )
            sys.exit(1)

    venv_path = Path(venv).resolve()
    contract_dir = contract_path.parent

    # Determine output path if not specified
    if not output:
        output = f"{contract_path.stem}.wasm"
    output_path = Path(output).resolve()

    # Check for reproducible build configuration if not in non-reproducible mode
    if not non_reproducible:
        has_config = check_reproducible_config()
        if not has_config:
            console.print(
                "[yellow]Reproducible build configuration not found in pyproject.toml"
            )
            console.print(
                "[yellow]For contract verification, it's recommended to initialize reproducible build config"
            )
            console.print(
                "[cyan]Run: nearc --init-reproducible-config to set up reproducible builds"
            )
            console.print("[yellow]Continuing with non-reproducible build...\n")
            non_reproducible = True

    # Display warning for non-reproducible builds
    if non_reproducible:
        console.print(
            "[yellow]Warning: Building in non-reproducible mode. This build cannot be verified on-chain.[/]"
        )
        console.print(
            "[yellow]Use the default reproducible mode for production deployments.[/]"
        )
    else:
        # Run reproducible build in Docker
        from .reproducible import run_reproducible_build

        # Prepare build args
        build_args = []
        if rebuild:
            build_args.append("--rebuild")
        if single_file:
            build_args.append("--single-file")

        console.print(
            "[green]Building in reproducible mode for contract verification[/]"
        )
        if not run_reproducible_build(contract_path, output_path, build_args):
            console.print("[red]Failed to run reproducible build")
            sys.exit(1)

        sys.exit(0)

    # Non-reproducible build flow:
    # Check for container environment and set up venv if needed
    in_container = is_running_in_container()
    if in_container:
        console.print(
            "[cyan]Detected running in container, setting up environment automatically[/]"
        )
        if not setup_venv(venv_path, contract_dir):
            console.print("[red]Failed to set up virtual environment in container")
            sys.exit(1)
    elif create_venv:
        # User explicitly requested venv setup
        if not setup_venv(venv_path, contract_dir):
            console.print("[red]Failed to set up virtual environment")
            sys.exit(1)
    elif not venv_path.exists():
        console.print(f"[red]Error: Virtual environment not found at {venv_path}")
        console.print("[cyan]Create one with: uv init")
        console.print("[cyan]Or run with --create-venv to create it automatically")
        sys.exit(1)

    # Check that emcc is available
    if not shutil.which("emcc"):
        console.print("[red]Error: Emscripten compiler (emcc) not found in PATH")
        console.print(
            "[cyan]Please install Emscripten: https://emscripten.org/docs/getting_started/"
        )
        sys.exit(1)

    # Determine assets directory
    assets_dir = Path(__file__).parent
    if not (assets_dir / "micropython").exists():
        console.print(
            f"[red]Error: MicroPython assets not found at {assets_dir / 'micropython'}"
        )
        sys.exit(1)

    # Compile the contract
    if not compile_contract(
        contract_path, output_path, venv_path, assets_dir, rebuild, single_file
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
