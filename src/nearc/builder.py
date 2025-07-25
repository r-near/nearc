#!/usr/bin/env python3
"""
WebAssembly build tools for the NEAR Python contract compiler.
"""

import shutil
import sys
from pathlib import Path
from typing import Set

from cpython_near_wasm_opt import optimize_wasm_file
from near_abi_py import generate_abi_from_files

from .abi import inject_abi
from .analyzer import analyze_contract, find_imports
from .exports import inject_contract_exports
from .manifest import prepare_build_files
from .metadata import inject_metadata_function
from .utils import console, find_site_packages, run_command_with_progress, with_progress


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

    # Inject exports for class-based contracts
    contract_with_exports = inject_contract_exports(contract_path)

    # Inject ABI
    contract_with_abi = inject_abi(contract_with_exports)

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

    if contract_with_abi != contract_path and contract_with_abi.exists():
        contract_with_abi.unlink()

    if contract_with_exports != contract_path and contract_with_exports.exists():
        contract_with_exports.unlink()

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


def compile_contract_cpython(
    contract_path: Path,
    output_path: Path,
    venv_path: Path,
    rebuild: bool = False,
    single_file: bool = False,
    module_tracing: bool = True,
    function_tracing: str = "safe",  # valid values: "aggressive", "safe", "safest", "off"
    compression: bool = True,
    debug_info: bool = True,
    pinned_functions: list[str] = [],
    verify_optimized_wasm: bool = True,
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

    # Ensure build directory exists
    if rebuild and build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)

    # Show a header for the compilation
    console.print(f"[bold cyan]Compiling NEAR Contract:[/] [yellow]{contract_path}[/]")
    if single_file:
        console.print("[cyan]Single file mode: skipping local module discovery[/]")

    # Inject exports for class-based contracts
    contract_with_exports = inject_contract_exports(contract_path)

    # Inject ABI
    contract_with_abi = inject_abi(contract_with_exports)

    # Inject metadata if needed
    contract_with_metadata = inject_metadata_function(contract_with_abi)

    # Use the potentially modified contract for compilation
    # We'll analyze the original contract for exports and imports first to avoid confusion
    exports, imports = analyze_contract(contract_path)

    # Add any additional imports needed for metadata
    if contract_with_metadata != contract_path:
        metadata_imports = find_imports(contract_with_metadata)
        imports = imports.union(metadata_imports)

    # Check if pyproject.toml has pinned functions specified
    pyproject_path = contract_path.parent / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            import tomllib

            with open(pyproject_path, "rb") as file:
                pyproject_data = tomllib.load(file)
            pinned_functions.extend(
                pyproject_data.get("tool", {})
                .get("nearc", {})
                .get("pinned-functions", [])
            )
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not read pinned functions from pyproject.toml: {e}"
            )

    # This is a directory where all modules destined for the compiled WASM should be stored,
    # including NEAR Python SDK files and any dependencies beyond the Python standard library
    # Python source files (.py) are required since they need be compiled into version-specific .pyc file by the WASM optimizer
    user_lib_dir = build_dir / "lib"
    shutil.copytree(find_site_packages(venv_path), user_lib_dir, dirs_exist_ok=True)

    # ABI can be utilized by the WASM optimizer to generate test cases for the module/function profiling
    abi = generate_abi_from_files(
        file_paths=[str(contract_path)], project_dir=str(contract_path.parent)
    )

    # Build the WASM contract
    optimize_wasm_file(
        build_dir=build_dir,
        output_file=output_path,
        module_opt=module_tracing,
        function_opt=function_tracing,
        compression=compression,
        debug_info=debug_info,
        pinned_functions=pinned_functions,
        user_lib_dir=user_lib_dir,
        contract_file=contract_with_metadata,
        contract_exports=exports,
        verify_optimized_wasm=verify_optimized_wasm,
        abi=abi,
    )

    # Clean up temporary file if we created one
    if contract_with_metadata != contract_path and contract_with_metadata.exists():
        contract_with_metadata.unlink()

    if contract_with_abi != contract_path and contract_with_abi.exists():
        contract_with_abi.unlink()

    if contract_with_exports != contract_path and contract_with_exports.exists():
        contract_with_exports.unlink()

    # Verify the output file exists
    if not output_path.exists():
        console.print(f"[red]Error: Output file {output_path} was not created")
        return False

    # Show success message with file size
    size_kb = output_path.stat().st_size / 1024
    console.print(
        f"[bold green]Successfully compiled contract:[/] [cyan]{output_path}[/] [yellow]({size_kb:.1f} KB)[/]"
    )
    if size_kb >= 1536:
        console.print(
            "[bold red]Compiled contract size exceeds 1.5MB limit[/], you could try re-running the build with a higher "
            "optimization level (-O[0-4]) and/or switching off the WASM debug info with --no-debug-info to reduce the size"
        )
    return True
