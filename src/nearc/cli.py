#!/usr/bin/env python3
"""
Command-line interface for the NEAR Python contract compiler.
"""

import shutil
import sys
from pathlib import Path
from typing import Optional

import rich_click as click

from .builder import compile_contract, compile_contract_cpython
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


@click.command()
@click.argument(
    "contract", type=click.Path(exists=True, dir_okay=False), required=False
)
@click.option("--output", "-o", help="Output WASM file path")
@click.option("--venv", help="Path to virtual environment", default=".venv")
@click.option("--rebuild", is_flag=True, help="Force a clean rebuild")
@click.option(
    "--reproducible", is_flag=True, help="Build reproducibly in Docker container"
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
@click.option(
    "--compiler",
    type=click.Choice(("mpy", "py")),
    default="mpy",
    help="Select which Python implementation to use (mpy: MicroPython, py: CPython)",
)
@click.option(
    "--opt-level",
    "-O",
    type=click.IntRange(0, 5),
    default=4,
    help="(CPython only) Optimization level (0-5)",
)
@click.option(
    "--module-tracing/--no-module-tracing",
    is_flag=True,
    default=None,
    help="(CPython only) Enable Python module tracing",
)
@click.option(
    "--function-tracing",
    type=click.Choice(("off", "safest", "safe", "aggressive")),
    default=None,
    help="(CPython only) Function tracing mode",
)
@click.option(
    "--compression/--no-compression",
    is_flag=True,
    default=None,
    help="(CPython only) Enable WASM data initializer compression",
)
@click.option(
    "--debug-info/--no-debug-info",
    is_flag=True,
    default=None,
    help="(CPython only) Include WASM debug information",
)
@click.option(
    "--verify-optimized-wasm",
    is_flag=True,
    default=False,
    help="(CPython only) Run/verify optimized WASM after building",
)
@click.option(
    "--pinned-functions",
    type=str,
    help="(CPython only) Comma-separated list of function names to pin (case-sensitive)",
)
def main(
    contract: Optional[str],
    output: Optional[str],
    venv: str,
    rebuild: bool,
    reproducible: bool,
    init_reproducible_config: bool,
    single_file: bool,
    create_venv: bool,
    compiler: str,
    opt_level: int,
    module_tracing: bool,
    function_tracing: str,
    compression: bool,
    debug_info: bool,
    verify_optimized_wasm: bool,
    pinned_functions: str,
):
    """Compile a Python contract to WebAssembly for NEAR blockchain.

    If CONTRACT is not specified, looks for __init__.py or main.py in the current directory.
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

    # If reproducible flag is set, build in Docker
    if reproducible:
        from .reproducible import run_reproducible_build

        # Prepare build args
        build_args = []
        if rebuild:
            build_args.append("--rebuild")
        if single_file:
            build_args.append("--single-file")

        # Run reproducible build in Docker
        if not run_reproducible_build(contract_path, output_path, build_args):
            console.print("[red]Failed to run reproducible build")
            sys.exit(1)

        sys.exit(0)

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

    if compiler == "mpy":
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
    elif compiler == "py":
        # defaults by optimization level: [module_tracing, function_tracing, compression, debug_info]
        defaults = {
            0: [False, "off", False, True],
            1: [True, "off", True, True],
            2: [True, "safest", True, True],
            3: [True, "safe", True, True],
            4: [True, "aggressive", True, True],
            5: [True, "aggressive", True, False],
        }[opt_level]

        module_tracing = defaults[0] if module_tracing is None else module_tracing
        function_tracing = function_tracing or str(defaults[1])
        compression = defaults[2] if compression is None else compression
        debug_info = defaults[3] if debug_info is None else debug_info

        # Compile the contract
        if not compile_contract_cpython(
            contract_path,
            output_path,
            venv_path,
            rebuild,
            single_file,
            module_tracing,
            function_tracing,
            compression,
            debug_info,
            [f.strip() for f in (pinned_functions or "").split(",") if f.strip()],
            verify_optimized_wasm,
        ):
            sys.exit(1)


if __name__ == "__main__":
    main()
