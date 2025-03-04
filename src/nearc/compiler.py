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
from typing import Set, List, Optional, Callable, Any

import rich_click as click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TaskID


console = Console()

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
            console.print(
                f"[yellow]Warning: Could not read exclusions from pyproject.toml: {e}"
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
        included_stdlib_packages = set(MPY_STDLIB_PACKAGES) - set(
            excluded_stdlib_packages
        )
        f.write(
            "\n".join(f'require("{module}")' for module in included_stdlib_packages)
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

        # Print warnings for missing modules separately before generating build files
        # This is key change #1 - move these warnings to print before the "Generating build files" message
        # The actual printing is done in prepare_build_files function

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

        for export in exports:
            f.write(f"void {export}() {{\n")
            f.write(f'    run_frozen_fn("{contract_name}", "{export}");\n')
            f.write("}\n\n")

    return wrappers_path


def run_command_with_progress(
    cmd: List[str],
    cwd: Optional[Path] = None,
    track_task_id: Optional[TaskID] = None,
    progress: Optional[Progress] = None,
    description: Optional[str] = None,
) -> bool:
    """
    Run a shell command and handle errors with live output.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command
        track_task_id: Task ID in the progress bar to update
        progress: Progress instance for updating task status
        description: Description to show in the progress bar

    Returns:
        True if the command succeeded, False if it failed
    """
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Use the provided description or default to the command
        display_description = description or f"Running: {' '.join(cmd[:2])}"

        # Read and display output in real-time
        output_lines = []
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break
                output_lines.append(line.strip())
                if progress and track_task_id is not None:
                    progress.update(track_task_id, description=display_description)

        # Wait for process to complete
        return_code = process.wait()

        if return_code != 0:
            output_str = "\n".join(output_lines)
            console.print(f"[red]Command failed with exit code {return_code}:")
            console.print(f"[red]{' '.join(cmd)}")
            if output_str:
                console.print(f"[red]Command output:[/]\n{output_str}")
            return False

        return True
    except Exception as e:
        console.print(f"[red]Error running command: {e}")
        console.print(f"[red]{' '.join(cmd)}")
        return False


def with_progress(description: str) -> Callable:
    """
    Decorator for functions that should show a progress indicator.

    Args:
        description: Description of the task

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use a custom TimeElapsedColumn that shows seconds instead of HH:MM:SS
            class SecondsElapsedColumn(TimeElapsedColumn):
                def render(self, task):
                    elapsed = task.finished_time if task.finished else task.elapsed
                    return f"[yellow]{elapsed:.1f}s"

            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                SecondsElapsedColumn(),
            ) as progress:
                task = progress.add_task(description, total=None)
                result = func(*args, **kwargs, progress=progress, task_id=task)
                return result

        return wrapper

    return decorator


def analyze_contract(contract_path: Path) -> tuple[Set[str], Set[str]]:
    """
    Analyze a contract file to find exports and imports.

    Args:
        contract_path: Path to the contract file

    Returns:
        Tuple of (exports, imports)
    """
    console.print("[cyan]Analyzing contract...[/]", end="")
    exports = find_exports(contract_path)
    imports = find_imports(contract_path)

    # Show analysis results
    if not exports:
        console.print(" [yellow]No exported functions found[/]")
    else:
        console.print(
            f" found [cyan]{len(exports)}[/] exported functions: [cyan]{', '.join(sorted(exports))}[/]"
        )

    return exports, imports


def prepare_build_files(
    contract_path: Path,
    imports: Set[str],
    exports: Set[str],
    venv_path: Path,
    build_dir: Path,
    site_packages: Path,
) -> tuple[Path, Path]:
    """
    Generate the manifest and wrappers files.

    Args:
        contract_path: Path to the contract file
        imports: Set of imported module names
        exports: Set of exported function names
        venv_path: Path to the virtual environment
        build_dir: Path to the build directory
        site_packages: Path to site-packages directory

    Returns:
        Tuple of (manifest_path, wrappers_path)
    """
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
        f"EXPORTED_FUNCTIONS={','.join(['_' + e for e in exports])}",
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
) -> bool:
    """
    Compile a NEAR contract to WebAssembly with progress display.

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

    # Show a header for the compilation
    console.print(f"[bold cyan]Compiling NEAR Contract:[/] [yellow]{contract_path}[/]")

    # Analyze the contract
    exports, imports = analyze_contract(contract_path)

    # Find site-packages directory
    site_packages = find_site_packages(venv_path)
    if not site_packages:
        console.print(f"[red]Error: Could not find site-packages in {venv_path}")
        sys.exit(1)

    # Generate build files - pass site_packages to allow warnings to be printed first
    manifest_file, wrappers_path = prepare_build_files(
        contract_path, imports, exports, venv_path, build_dir, site_packages
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
