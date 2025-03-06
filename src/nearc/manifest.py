#!/usr/bin/env python3
"""
Build manifest generation for the NEAR Python contract compiler.
"""

import os
from pathlib import Path
from typing import Set, List

from .analyzer import is_micropython_module, get_excluded_stdlib_packages
from .utils import console, find_site_packages


def generate_manifest(
    contract_path: Path, imports: Set[str], venv_path: Path, build_dir: Path
) -> tuple[Path, List[str]]:
    """
    Generate a MicroPython manifest file that includes all necessary modules.

    Args:
        contract_path: Path to the contract file
        imports: Set of imported module names
        venv_path: Path to the virtual environment
        build_dir: Path to the build directory

    Returns:
        Tuple of (manifest_path, missing_modules)
    """
    manifest_path = build_dir / "manifest.py"
    site_packages = find_site_packages(venv_path)

    if not site_packages:
        console.print(f"[red]Error: Could not find site-packages in {venv_path}")
        import sys

        sys.exit(1)

    # Get excluded packages
    excluded_stdlib_packages = get_excluded_stdlib_packages(contract_path.parent)
    if excluded_stdlib_packages:
        console.print(
            f"Excluding MicroPython stdlib packages: {', '.join(excluded_stdlib_packages)}"
        )

    with open(manifest_path, "w") as f:
        f.write("# THIS FILE IS GENERATED, DO NOT EDIT\n\n")

        # Add stdlib packages
        from .analyzer import MPY_STDLIB_PACKAGES

        included_stdlib_packages = set(MPY_STDLIB_PACKAGES) - set(
            excluded_stdlib_packages
        )

        f.write(
            "\n".join(
                f'require("{module}")'
                for module in sorted(included_stdlib_packages)  # Deterministic builds
            )
        )

        # Add typing modules
        f.write("\n\n# Typing modules\n")
        f.write(
            "\n".join(
                f'module("{mod}.py", base_path="$(PORT_DIR)/extra/typing")'
                for mod in ["typing", "typing_extensions"]
            )
        )

        # Find external dependencies (non-MicroPython modules)
        external_modules = {
            name.split(".")[0] for name in imports if not is_micropython_module(name)
        }

        # Process external dependencies
        external_deps = []
        rel_path = os.path.relpath(site_packages, manifest_path.parent).replace(
            "\\", "/"
        )

        missing_modules = []
        for base_module in external_modules:
            module_dir = site_packages / base_module
            module_file = site_packages / f"{base_module}.py"

            if module_dir.is_dir():
                external_deps.append(
                    f'package("{base_module}", base_path="{rel_path}")'
                )
            elif module_file.exists():
                external_deps.append(
                    f'module("{base_module}.py", base_path="{rel_path}")'
                )
            else:
                missing_modules.append(base_module)

        if external_deps:
            f.write("\n\n# External dependencies\n")
            f.write("\n".join(external_deps))

        # Include the contract file
        f.write("\n\n# Contract\n")
        f.write(f'module("{contract_path.name}", base_path="..")')

    return manifest_path, missing_modules


def generate_export_wrappers(
    exports: Set[str], contract_name: str, build_dir: Path
) -> Path:
    """
    Generate C wrappers for exported functions.

    Args:
        exports: Set of exported function names
        contract_name: Name of the contract file
        build_dir: Path to the build directory

    Returns:
        Path to the generated wrappers file
    """
    wrappers_path = build_dir / "export_wrappers.c"

    with open(wrappers_path, "w") as f:
        f.write("/* Generated export wrappers for NEAR contract */\n\n")
        f.write("void run_frozen_fn(const char *file_name, const char *fn_name);\n\n")

        for export in sorted(exports):
            f.write(f"void {export}() {{\n")
            f.write(f'    run_frozen_fn("{contract_name}", "{export}");\n')
            f.write("}\n\n")

    return wrappers_path


def prepare_build_files(
    contract_path: Path,
    imports: Set[str],
    exports: Set[str],
    venv_path: Path,
    build_dir: Path,
) -> tuple[Path, Path]:
    """
    Generate the manifest and wrappers files.

    Args:
        contract_path: Path to the contract file
        imports: Set of imported module names
        exports: Set of exported function names
        venv_path: Path to the virtual environment
        build_dir: Path to the build directory

    Returns:
        Tuple of (manifest_path, wrappers_path)
    """
    # Find site-packages directory
    site_packages = find_site_packages(venv_path)
    if not site_packages:
        console.print(f"[red]Error: Could not find site-packages in {venv_path}")
        import sys

        sys.exit(1)

    # Generate manifest and get missing modules
    manifest_result, missing_modules = generate_manifest(
        contract_path, imports, venv_path, build_dir
    )

    # Print warnings for missing modules before the "Generating build files" message
    for module in missing_modules:
        console.print(
            f"[yellow]Warning: Could not find module {module} in {site_packages}"
        )

    console.print("[cyan]Generating build files...[/]", end="")

    # Generate wrappers
    wrappers_path = generate_export_wrappers(exports, contract_path.name, build_dir)

    console.print(" done")

    return manifest_result, wrappers_path
