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
from .utils import console


@click.command()
@click.argument("contract", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", help="Output WASM file path")
@click.option("--venv", help="Path to virtual environment", default=".venv")
@click.option("--rebuild", is_flag=True, help="Force a clean rebuild")
def main(contract: str, output: Optional[str], venv: str, rebuild: bool):
    """Compile a Python contract to WebAssembly for NEAR blockchain."""
    # Resolve paths
    contract_path = Path(contract).resolve()
    venv_path = Path(venv).resolve()

    # Determine output path if not specified
    if not output:
        output = f"{contract_path.stem}.wasm"
    output_path = Path(output).resolve()

    # Check that virtual environment exists
    if not venv_path.exists():
        console.print(f"[red]Error: Virtual environment not found at {venv_path}")
        console.print("[cyan]Create one with: uv init")
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
    if not compile_contract(contract_path, output_path, venv_path, assets_dir, rebuild):
        sys.exit(1)


if __name__ == "__main__":
    main()
