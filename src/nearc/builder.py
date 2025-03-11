#!/usr/bin/env python3
"""
WebAssembly build tools for the NEAR Python contract compiler.
"""

import shutil
import sys
from pathlib import Path
from typing import Set

from .analyzer import analyze_contract, find_imports
from .manifest import prepare_build_files
from .metadata import inject_metadata_function
from .utils import console, run_command_with_progress, with_progress
from .abi import inject_abi


@with_progress("Building MicroPython cross-compiler")
def build_mpy_cross(
    mpy_cross_dir: Path,
    build_dir: Path,
    rebuild: bool = False,
    progress=None,
    task_id=None,
) -> Path:
    """
    Build the MicroPython cross-compiler.

    Args:
        mpy_cross_dir: Path to the mpy-cross directory
        build_dir: Path to the build directory
        rebuild: Whether to force a rebuild
        progress: Progress instance
        task_id: Task ID in the progress bar

    Returns:
        Path to the mpy-cross executable
    """
    mpy_cross_build_dir = build_dir / "mpy-cross"
    mpy_cross_exe = mpy_cross_build_dir / "mpy-cross"

    if mpy_cross_exe.exists() and not rebuild:
        # Skip showing the progress bar completely for cached builds
        if progress:
            progress.stop()
        console.print("[cyan]Using existing MicroPython cross-compiler[/]")
        return mpy_cross_exe

    # Only reach here if we need to build
    mpy_cross_build_dir.mkdir(exist_ok=True)

    if not run_command_with_progress(
        ["make", "-C", str(mpy_cross_dir), f"BUILD={mpy_cross_build_dir}"],
        track_task_id=task_id,
        progress=progress,
        description="Building MicroPython cross-compiler",
    ):
        console.print("[red]Failed to build MicroPython cross-compiler")
        sys.exit(1)

    return mpy_cross_exe


@with_progress("Compiling WebAssembly contract")
def build_wasm(
    mpy_port_dir: Path,
    build_dir: Path,
    mpy_cross_exe: Path,
    manifest_path: Path,
    wrappers_path: Path,
    exports: Set[str],
    output_path: Path,
    progress=None,
    task_id=None,
) -> bool:
    """
    Build the WebAssembly contract.

    Args:
        mpy_port_dir: Path to the MicroPython port directory
        build_dir: Path to the build directory
        mpy_cross_exe: Path to the mpy-cross executable
        manifest_path: Path to the manifest file
        wrappers_path: Path to the wrappers file
        exports: Set of exported function names
        output_path: Path where the output WASM should be written
        progress: Progress instance
        task_id: Task ID in the progress bar

    Returns:
        True if compilation succeeded, False if it failed
    """
    # Remove any existing frozen content file to force regeneration
    frozen_content_path = build_dir / "frozen_content.c"
    if frozen_content_path.exists():
        frozen_content_path.unlink()

    # Build command
    build_cmd = [
        "make",
        "-C",
        str(mpy_port_dir),
        f"BUILD={build_dir}",
        f"MICROPY_MPYCROSS={mpy_cross_exe}",
        f"MICROPY_MPYCROSS_DEPENDENCY={mpy_cross_exe}",
        f"FROZEN_MANIFEST={manifest_path}",
        f"SRC_C_GENERATED={wrappers_path}",
        f"EXPORTED_FUNCTIONS={','.join(['_' + e for e in sorted(exports)])}",
        f"OUTPUT_WASM={output_path}",
    ]

    return run_command_with_progress(
        build_cmd,
        track_task_id=task_id,
        progress=progress,
        description="Compiling WebAssembly contract",
    )


def compile_contract(
    contract_path: Path,
    output_path: Path,
    venv_path: Path,
    assets_dir: Path,
    rebuild: bool = False,
    single_file: bool = False,
) -> bool:
    """
    Compile a NEAR contract to WebAssembly with progress display.

    Args:
        contract_path: Path to the contract file
        output_path: Path where the output WASM should be written
        venv_path: Path to the virtual environment
        assets_dir: Path to the assets directory
        rebuild: Whether to force a clean rebuild
        single_file: Whether to skip local module discovery and compile only the specified file

    Returns:
        True if compilation succeeded, False if it failed
    """
    # Setup paths
    build_dir = contract_path.parent / "build"
    mpy_cross_dir = assets_dir / "micropython" / "mpy-cross"
    mpy_port_dir = assets_dir / "micropython" / "ports" / "webassembly-near"

    # Ensure build directory exists
    if rebuild and build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)

    # Show a header for the compilation
    console.print(f"[bold cyan]Compiling NEAR Contract:[/] [yellow]{contract_path}[/]")
    if single_file:
        console.print("[cyan]Single file mode: skipping local module discovery[/]")

    # Inject ABI
    contract_with_abi = inject_abi(contract_path)

    # Inject metadata if needed
    contract_with_metadata = inject_metadata_function(contract_with_abi)

    # Use the potentially modified contract for compilation
    # We'll analyze the original contract for exports and imports first to avoid confusion
    exports, imports = analyze_contract(contract_path)

    # Add any additional imports needed for metadata
    if contract_with_metadata != contract_path:
        metadata_imports = find_imports(contract_with_metadata)
        imports = imports.union(metadata_imports)

    # Generate build files
    manifest_file, wrappers_path = prepare_build_files(
        contract_with_metadata, imports, exports, venv_path, build_dir, single_file
    )

    # Build MicroPython cross-compiler if needed
    mpy_cross_exe = build_mpy_cross(mpy_cross_dir, build_dir, rebuild)

    # Build the WASM contract
    if not build_wasm(
        mpy_port_dir,
        build_dir,
        mpy_cross_exe,
        manifest_file,
        wrappers_path,
        exports,
        output_path,
    ):
        console.print("[red]Failed to build WebAssembly contract")
        return False

    # Clean up temporary file if we created one
    if contract_with_metadata != contract_path and contract_with_metadata.exists():
        contract_with_metadata.unlink()

    if contract_with_abi.exists():
        contract_with_abi.unlink()

    # Verify the output file exists
    if not output_path.exists():
        console.print(f"[red]Error: Output file {output_path} was not created")
        return False

    # Show success message with file size
    size_kb = output_path.stat().st_size / 1024
    console.print(
        f"[bold green]Successfully compiled contract:[/] [cyan]{output_path}[/] [yellow]({size_kb:.1f} KB)[/]"
    )
    return True
