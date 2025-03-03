#!/usr/bin/env python3
"""
nearc - A simple compiler for NEAR Python contracts

This tool converts Python smart contracts to WebAssembly for deployment on the NEAR blockchain.
"""

import ast
import os
import shutil
import sys
import subprocess
import tomllib
from pathlib import Path
from typing import Set, List, Optional

import rich_click as click

MPY_MODULES = {"array", "builtins", "json", "os", "random", "struct", "sys"}
MPY_LIB_PACKAGES = {"aiohttp", "cbor2", "iperf3", "pyjwt", "requests"}
MPY_STDLIB_PACKAGES = [
    "binascii",
    "contextlib",
    "fnmatch",
    "hashlib-sha224",
    "hmac",
    "keyword",
    "os-path",
    "pprint",
    "stat",
    "tempfile",
    "types",
    "warnings",
    "__future__",
    "bisect",
    "copy",
    "functools",
    "hashlib-sha256",
    "html",
    "locale",
    "pathlib",
    "quopri",
    "string",
    "textwrap",
    "unittest",
    "zlib",
    "abc",
    "cmd",
    "curses.ascii",
    "gzip",
    "hashlib-sha384",
    "inspect",
    "logging",
    "pickle",
    "random",
    "struct",
    "threading",
    "unittest-discover",
    "argparse",
    "collections",
    "datetime",
    "hashlib",
    "hashlib-sha512",
    "io",
    "operator",
    "pkg_resources",
    "shutil",
    "tarfile",
    "time",
    "uu",
    "base64",
    "collections-defaultdict",
    "errno",
    "hashlib-core",
    "heapq",
    "itertools",
    "os",
    "pkgutil",
    "ssl",
    "tarfile-write",
    "traceback",
    "venv",
]
NEAR_MODULE_NAME = "near"


def find_exports(file_path: Path) -> Set[str]:
    """
    Find all functions decorated with NEAR export decorators in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Set of function names that are marked as NEAR exports
    """
    with open(file_path) as f:
        tree = ast.parse(f.read())

    export_decorators = {"export", "view", "call", "init", "callback", "near.export"}
    exports = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.decorator_list:
            continue

        for decorator in node.decorator_list:
            name = None

            # Simple name: @export
            if isinstance(decorator, ast.Name):
                name = decorator.id
            # Call: @export()
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Name
            ):
                name = decorator.func.id
            # Attribute: @near.export
            elif isinstance(decorator, ast.Attribute) and isinstance(
                decorator.value, ast.Name
            ):
                if decorator.value.id == "near" and decorator.attr == "export":
                    name = "near.export"

            if name in export_decorators:
                exports.add(node.name)
                break

    return exports


def find_imports(file_path: Path) -> Set[str]:
    """
    Find all imported modules in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Set of module names that are imported
    """
    with open(file_path) as f:
        tree = ast.parse(f.read())

    imports = set()

    for node in ast.walk(tree):
        # Direct imports: import foo, bar
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        # From imports: from foo import bar
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def is_micropython_module(module_name: str) -> bool:
    """Check if a module is included in MicroPython."""
    base_module = module_name.split(".")[0]
    return (
        base_module in MPY_MODULES
        or base_module in MPY_LIB_PACKAGES
        or base_module in MPY_STDLIB_PACKAGES
        or base_module == NEAR_MODULE_NAME
    )


def get_excluded_stdlib_packages(project_path: Path) -> List[str]:
    """Get excluded stdlib packages from pyproject.toml."""
    pyproject_path = project_path / "pyproject.toml"
    excluded_packages = []

    if pyproject_path.is_file():
        try:
            with open(pyproject_path, "rb") as file:
                pyproject_data = tomllib.load(file)
            excluded_packages = (
                pyproject_data.get("tool", {})
                .get("near-py-tool", {})
                .get("exclude-micropython-stdlib-packages", [])
            )
        except (ImportError, Exception) as e:
            click.echo(
                click.style(
                    f"Warning: Could not read exclusions from pyproject.toml: {e}",
                    fg="yellow",
                )
            )

    return excluded_packages


def find_site_packages(venv_path: Path) -> Optional[Path]:
    """
    Find the site-packages directory in a virtual environment.

    Args:
        venv_path: Path to the virtual environment

    Returns:
        Path to the site-packages directory, or None if not found
    """
    # Common locations for site-packages
    candidates = [
        venv_path / "lib" / "site-packages",  # Unix/macOS
        venv_path / "Lib" / "site-packages",  # Windows
    ]

    # Check each candidate
    for path in candidates:
        if path.is_dir():
            return path

    # If not found, try to find it with glob patterns
    for pattern in ["lib/python*/site-packages", "Lib/Python*/site-packages"]:
        matches = list(venv_path.glob(pattern))
        if matches:
            return matches[0]

    return None


def generate_manifest(
    contract_path: Path, imports: Set[str], venv_path: Path, build_dir: Path
) -> Path:
    """
    Generate a MicroPython manifest file that includes all necessary modules.

    Args:
        contract_path: Path to the contract file
        imports: Set of imported module names
        venv_path: Path to the virtual environment
        build_dir: Path to the build directory

    Returns:
        Path to the generated manifest file
    """
    manifest_path = build_dir / "manifest.py"
    site_packages = find_site_packages(venv_path)

    if not site_packages:
        click.echo(
            click.style(f"Error: Could not find site-packages in {venv_path}", fg="red")
        )
        sys.exit(1)

    # Get excluded packages
    excluded_stdlib_packages = get_excluded_stdlib_packages(contract_path.parent)
    if excluded_stdlib_packages:
        click.echo(
            f"Excluding MicroPython stdlib packages: {', '.join(excluded_stdlib_packages)}"
        )

    with open(manifest_path, "w") as f:
        f.write("# THIS FILE IS GENERATED, DO NOT EDIT\n\n")

        # Add stdlib packages
        for module in MPY_STDLIB_PACKAGES:
            if module not in excluded_stdlib_packages:
                f.write(f'require("{module}")\n')

        # Add typing modules
        f.write("\n# Typing modules\n")
        for mod in ["typing", "typing_extensions"]:
            f.write(f'module("{mod}.py", base_path="$(PORT_DIR)/extra/typing")\n')

        # Add external dependencies
        external_deps_added = False
        for module_name in imports:
            if not is_micropython_module(module_name):
                if not external_deps_added:
                    f.write("\n# External dependencies\n")
                    external_deps_added = True

                # Get base module name (before first dot)
                base_module = module_name.split(".")[0]

                # Process module
                module_dir = site_packages / base_module
                module_file = site_packages / f"{base_module}.py"

                if module_dir.is_dir() or module_file.exists():
                    rel_path = os.path.relpath(site_packages, manifest_path.parent)
                    base_path = str(Path(rel_path)).replace("\\", "/")

                    if module_dir.is_dir():
                        f.write(f'package("{base_module}", base_path="{base_path}")\n')
                    else:
                        f.write(
                            f'module("{base_module}.py", base_path="{base_path}")\n'
                        )
                else:
                    click.echo(
                        click.style(
                            f"Warning: Could not find module {base_module} in {site_packages}",
                            fg="yellow",
                        )
                    )

        # Include the contract file
        f.write("\n# Contract\n")
        f.write(f'module("{contract_path.name}", base_path="..")\n')

    return manifest_path


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

        for export in exports:
            f.write(f"void {export}() {{\n")
            f.write(f'    run_frozen_fn("{contract_name}", "{export}");\n')
            f.write("}\n\n")

    return wrappers_path


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """
    Run a shell command and handle errors.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command

    Returns:
        True if the command succeeded, False if it failed
    """
    try:
        subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=False,
            text=True,
        )

        return True
    except Exception as e:
        click.echo(click.style(f"Error running command: {e}", fg="red"))
        return False


def compile_contract(
    contract_path: Path,
    output_path: Path,
    venv_path: Path,
    assets_dir: Path,
    rebuild: bool = False,
) -> bool:
    """
    Compile a NEAR contract to WebAssembly.

    Args:
        contract_path: Path to the contract file
        output_path: Path where the output WASM should be written
        venv_path: Path to the virtual environment
        assets_dir: Path to the assets directory
        rebuild: Whether to force a clean rebuild

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

    # Analyze the contract
    click.echo(click.style(f"Analyzing contract: {contract_path}", fg="cyan"))
    exports = find_exports(contract_path)
    imports = find_imports(contract_path)

    if not exports:
        click.echo(
            click.style(
                "Warning: No exported functions found in the contract", fg="yellow"
            )
        )
    else:
        click.echo(
            click.style(
                f"Found {len(exports)} exported functions: {', '.join(exports)}",
                fg="cyan",
            )
        )

    # Generate manifest
    click.echo(click.style("Generating build files...", fg="cyan"))
    manifest_path = generate_manifest(contract_path, imports, venv_path, build_dir)

    # Generate export wrappers
    wrappers_path = generate_export_wrappers(exports, contract_path.name, build_dir)

    # Build MicroPython cross-compiler if needed
    mpy_cross_build_dir = build_dir / "mpy-cross"
    mpy_cross_exe = mpy_cross_build_dir / "mpy-cross"

    if not mpy_cross_exe.exists() or rebuild:
        click.echo(click.style("Building MicroPython cross-compiler...", fg="cyan"))
        mpy_cross_build_dir.mkdir(exist_ok=True)

        if not run_command(
            ["make", "-C", str(mpy_cross_dir), f"BUILD={mpy_cross_build_dir}"]
        ):
            click.echo(
                click.style("Failed to build MicroPython cross-compiler", fg="red")
            )
            return False

    # Build the WASM contract
    click.echo(click.style("Compiling contract to WebAssembly...", fg="cyan"))

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
        f"EXPORTED_FUNCTIONS={','.join(['_' + e for e in exports])}",
        f"OUTPUT_WASM={output_path}",
    ]

    if not run_command(build_cmd):
        click.echo(click.style("Failed to build WebAssembly contract", fg="red"))
        return False

    # Verify the output file exists
    if not output_path.exists():
        click.echo(
            click.style(f"Error: Output file {output_path} was not created", fg="red")
        )
        return False

    # Show success message with file size
    size_kb = output_path.stat().st_size / 1024
    click.echo(click.style("Successfully compiled contract:", fg="green"), nl=False)
    click.echo(click.style(f" {output_path}", fg="cyan", bold=True), nl=False)
    click.echo(click.style(f" ({size_kb:.1f} KB)", fg="yellow"))
    return True


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
        click.echo(
            click.style(
                f"Error: Virtual environment not found at {venv_path}", fg="red"
            )
        )
        click.echo(click.style("Create one with: uv init", fg="cyan"))
        sys.exit(1)

    # Check that emcc is available
    if not shutil.which("emcc"):
        click.echo(
            click.style("Error: Emscripten compiler (emcc) not found in PATH", fg="red")
        )
        click.echo(
            click.style(
                "Please install Emscripten: https://emscripten.org/docs/getting_started/",
                fg="cyan",
            )
        )
        sys.exit(1)

    # Determine assets directory
    assets_dir = Path(__file__).parent
    if not (assets_dir / "micropython").exists():
        click.echo(
            click.style(
                f"Error: MicroPython assets not found at {assets_dir / 'micropython'}",
                fg="red",
            )
        )
        sys.exit(1)

    # Compile the contract
    if not compile_contract(contract_path, output_path, venv_path, assets_dir, rebuild):
        sys.exit(1)


if __name__ == "__main__":
    main()
