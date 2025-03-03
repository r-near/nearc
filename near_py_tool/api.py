import ast
import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path
from typing import Dict, List, Set

import click
import toml

from near_py_tool.run_command import is_command_available, run_command

# Constants for MicroPython modules and packages
MPY_MODULES = {"array", "builtins", "json", "os", "random", "struct", "sys"}
MPY_LIB_PACKAGES = {"aiohttp", "cbor2", "iperf3", "pyjwt", "requests"}
MPY_STDLIB_PACKAGES = [
    "binascii", "contextlib", "fnmatch", "hashlib-sha224", "hmac", "keyword", 
    "os-path", "pprint", "stat", "tempfile", "types", "warnings", "__future__", 
    "bisect", "copy", "functools", "hashlib-sha256", "html", "locale", "pathlib",
    "quopri", "string", "textwrap", "unittest", "zlib", "abc", "cmd", "curses.ascii",
    "gzip", "hashlib-sha384", "inspect", "logging", "pickle", "random", "struct",
    "threading", "unittest-discover", "argparse", "collections", "datetime", "hashlib",
    "hashlib-sha512", "io", "operator", "pkg_resources", "shutil", "tarfile", "time",
    "uu", "base64", "collections-defaultdict", "errno", "hashlib-core", "heapq",
    "itertools", "os", "pkgutil", "ssl", "tarfile-write", "traceback", "venv"
]
NEAR_MODULE_NAME = "near"


def get_near_exports_from_file(file_path: str) -> Set[str]:
    """Extract functions decorated with NEAR export decorators."""
    with open(file_path, "r") as file:
        content = file.read()
        tree = ast.parse(content, filename=file_path)

    # Set of potential decorators that might be NEAR exports
    near_export_decorators = {"export", "view", "call", "init", "callback", "near.export"}
    
    # Set to store exported function names
    exports = set()
    
    # Find all decorated functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            for decorator in node.decorator_list:
                decorator_name = None
                
                # Handle different decorator patterns
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Call):
                    decorator_name = decorator.func.id
                    print(decorator_name)
                elif isinstance(decorator, ast.Attribute) and isinstance(decorator.value, ast.Name):
                    if decorator.value.id == "near" and decorator.attr == "export":
                        decorator_name = "near.export"
                
                # If it's a NEAR export decorator, add the function name
                if decorator_name in near_export_decorators:
                    exports.add(node.name)
                    break
    
    return exports


def get_imports_from_file(file_path: Path) -> Set[str]:
    """Extract imported modules from a Python file."""
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    
    # Remove `near_py_tool` if it exists
    try:
        imports.remove("near_py_tool")
    except KeyError:
        pass

    return imports


def is_external_package(name: str) -> bool:
    """Determine if a package is external (not in MicroPython)."""
    return (
        name not in MPY_MODULES
        and name not in MPY_LIB_PACKAGES
        and name not in MPY_STDLIB_PACKAGES
        and name != NEAR_MODULE_NAME
    )


def generate_manifest(
    contract_path: Path, 
    venv_path: Path,
    imports: Set[str],
    manifest_path: Path, 
    excluded_stdlib_packages: List[str]
):
    """Generate the MicroPython manifest file."""
    with open(manifest_path, "w") as f:
        f.write("# THIS FILE IS GENERATED, DO NOT EDIT\n\n")
        
        # Add stdlib packages
        for module in MPY_STDLIB_PACKAGES:
            if module not in excluded_stdlib_packages:
                f.write(f'require("{module}")\n')
        
        # Add typing modules
        for mod in ["typing", "typing_extensions"]:
            f.write(f'module("{mod}.py", base_path="$(PORT_DIR)/extra/typing")\n')
        
        # Find site-packages directory
        site_packages = find_site_packages_dir(venv_path)
        if not site_packages:
            click.echo(click.style(
                f"Error: Could not find site-packages directory in {venv_path}",
                fg="bright_red"
            ))
            sys.exit(1)
            
        # Add external packages
        for module_name in imports:
            if is_external_package(module_name):
                # Get the base module name (before the first dot)
                base_module = module_name.split('.')[0]
                
                # Try to find the module directory
                module_dir = site_packages / base_module
                if module_dir.exists() and module_dir.is_dir():
                    # Calculate relative path from manifest to the package
                    rel_path = os.path.relpath(site_packages, manifest_path.parent)
                    # Use forward slashes for consistency across platforms
                    base_path = str(Path(rel_path)).replace("\\", "/")
                    f.write(f'package("{base_module}", base_path="{base_path}")\n')
                elif (site_packages / f"{base_module}.py").exists():
                    # Handle single-file modules
                    rel_path = os.path.relpath(site_packages, manifest_path.parent)
                    base_path = str(Path(rel_path)).replace("\\", "/")
                    f.write(f'module("{base_module}.py", base_path="{base_path}")\n')
                else:
                    click.echo(click.style(
                        f"Warning: Could not find module {base_module} in {site_packages}",
                        fg="bright_yellow"
                    ))
        
        # Add the contract itself
        f.write(f'module("{contract_path.name}", base_path="..")\n')


def generate_export_wrappers(contract_path: Path, exports: List[str], export_wrappers_path: Path):
    """Generate C export wrappers for the NEAR contract."""
    with open(export_wrappers_path, "w") as f:
        f.write("/* THIS FILE IS GENERATED, DO NOT EDIT */\n\n")
        f.write("void run_frozen_fn(const char *file_name, const char *fn_name);\n\n")
        
        for export in exports:
            f.write(f'void {export}() {{\n  run_frozen_fn("{contract_path.name}", "{export}");\n}}\n\n')


def find_site_packages_dir(venv_path: Path) -> Path:
    """Find the site-packages directory in a virtual environment created by uv."""
    # uv typically uses a simpler structure than standard venv
    site_packages = venv_path / "lib" / "site-packages"  # Unix/macOS
    
    if site_packages.is_dir():
        return site_packages
        
    # Windows path
    site_packages = venv_path / "Lib" / "site-packages"
    if site_packages.is_dir():
        return site_packages
    
    # If the standard paths don't exist, try to find it with a more general approach
    patterns = [
        "lib/python*/site-packages",         # Unix fallback
        "Lib/Python*/site-packages"          # Windows fallback
    ]
    
    for pattern in patterns:
        matches = list(venv_path.glob(pattern))
        if matches:
            return matches[0]
    
    return None


def get_excluded_stdlib_packages(project_path: Path) -> List[str]:
    """Get excluded stdlib packages from pyproject.toml."""
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.is_file():
        with open(pyproject_path, "r") as file:
            pyproject_data = toml.load(file)
        return pyproject_data.get("tool", {}).get("near-py-tool", {}).get("exclude-micropython-stdlib-packages", [])
    return []


def build(
    project_dir: str,
    rebuild_all: bool = False,
    contract_name: str = "contract.py",
):
    """Build a NEAR Python contract."""
    # Resolve paths
    project_path = Path(project_dir).resolve()
    project_name = project_path.name
    build_path = project_path / "build"
    mpy_cross_build_path = build_path / "mpy-cross"
    contract_path = project_path / contract_name
    venv_path = project_path / ".venv"
    
    # Get asset paths
    mpy_cross_path = files("near_py_tool") / "assets" / "micropython" / "mpy-cross"
    mpy_port_path = files("near_py_tool") / "assets" / "micropython" / "ports" / "webassembly-near"

    # Check that emcc command exists
    
    
    # Verify contract exists
    if not contract_path.is_file():
        click.echo(click.style(f"Error: Contract file {contract_path} doesn't exist", fg="bright_red"))
        sys.exit(1)
    
    # Verify .venv exists
    if not venv_path.is_dir():
        click.echo(
            click.style(
                f"Error: Virtual environment not found at {venv_path}.\n"
                f"Please run 'uv init' in your project directory to create it.",
                fg="bright_red"
            )
        )
        sys.exit(1)
    
    # Handle rebuild_all flag
    if rebuild_all:
        click.echo(f"Removing build directory {build_path} for clean build")
        try:
            shutil.rmtree(build_path)
        except Exception as e:
            click.echo(f"Warning: Failed to remove build directory: {e}")
    
    # Ensure build directory exists
    build_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Using virtual environment at {venv_path}")
    
    # Check that uv is available
    if not shutil.which("uv"):
        click.echo(
            click.style(
                "Warning: 'uv' not found in PATH. It's recommended for managing Python dependencies.",
                fg="bright_yellow"
            )
        )
    
    # Get imports and exports from contract
    imports = get_imports_from_file(contract_path)
    exports = list(get_near_exports_from_file(contract_path))
    
    if not exports:
        click.echo(
            click.style(
                "Warning: No NEAR export functions found in the contract. "
                "The contract will not expose any callable methods.",
                fg="bright_yellow"
            )
        )
    else:
        click.echo(f"Found {len(exports)} NEAR export methods: {', '.join(exports)}")
    
    # Generate build files
    excluded_stdlib_packages = get_excluded_stdlib_packages(project_path)
    if excluded_stdlib_packages:
        click.echo(f"Excluding MicroPython stdlib packages: {', '.join(excluded_stdlib_packages)}")
    
    # Generate manifest and export wrappers
    click.echo("Generating MicroPython manifest...")
    generate_manifest(
        contract_path,
        venv_path,
        imports,
        build_path / "manifest.py",
        excluded_stdlib_packages,
    )
    
    click.echo("Generating export wrappers...")
    generate_export_wrappers(
        contract_path, 
        exports, 
        build_path / "export_wrappers.c"
    )
    
    # Force rebuild of frozen content
    frozen_content_path = build_path / "frozen_content.c"
    if frozen_content_path.exists():
        frozen_content_path.unlink()
    
    # Determine output WASM path
    if contract_name != "contract.py":
        output_name = Path(contract_name).stem
    else:
        output_name = project_name
        
    contract_wasm_path = build_path / f"{output_name}.wasm"
    
    # Build mpy-cross if needed
    mpy_cross_exe = mpy_cross_build_path / "mpy-cross"
    if not mpy_cross_exe.exists() or rebuild_all:
        click.echo("Building MicroPython cross-compiler...")
        mpy_cross_build_path.mkdir(parents=True, exist_ok=True)
        run_command(
            ["make", "-C", str(mpy_cross_path), f"BUILD={mpy_cross_build_path}"],
            cwd=project_path,
        )
    
    # Build the WASM contract
    click.echo("Building WASM contract...")
    run_command(
        [
            "make",
            "-C",
            str(mpy_port_path),
            f"BUILD={build_path}",
            f"MICROPY_MPYCROSS={mpy_cross_build_path}/mpy-cross",
            f"MICROPY_MPYCROSS_DEPENDENCY={mpy_cross_build_path}/mpy-cross",
            f"FROZEN_MANIFEST={build_path / 'manifest.py'}",
            f"SRC_C_GENERATED={build_path / 'export_wrappers.c'}",
            f"EXPORTED_FUNCTIONS={','.join(['_' + e for e in exports])}",
            f"OUTPUT_WASM={contract_wasm_path}",
        ],
        cwd=project_path,
    )
    
    # Check if the build was successful
    if contract_wasm_path.exists():
        wasm_size = contract_wasm_path.stat().st_size / 1024  # Size in KB
        click.echo(click.style(
            f"✓ Contract built successfully: {contract_wasm_path} ({wasm_size:.1f} KB)",
            fg="green"
        ))
    else:
        click.echo(click.style(
            f"× Failed to build contract. Check the errors above.",
            fg="bright_red"
        ))
        sys.exit(1)
        
    return contract_wasm_path