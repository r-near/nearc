#!/usr/bin/env python3
"""
Code analysis tools for the NEAR Python contract compiler.
"""

import ast
import tomllib
from pathlib import Path
from typing import Set, List

from .utils import console

# MicroPython module lists for dependency analysis
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

    # Always include contract_source_metadata in exports
    # This ensures it's properly registered even if we need to inject it
    exports.add("contract_source_metadata")
    exports.add("__contract_abi")

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
    """
    Check if a module is included in MicroPython.

    Args:
        module_name: Name of the module to check

    Returns:
        True if the module is included in MicroPython, False otherwise
    """
    base_module = module_name.split(".")[0]
    return (
        base_module in MPY_MODULES
        or base_module in MPY_LIB_PACKAGES
        or base_module in MPY_STDLIB_PACKAGES
        or base_module == NEAR_MODULE_NAME
    )


def get_excluded_stdlib_packages(project_path: Path) -> List[str]:
    """
    Get excluded stdlib packages from pyproject.toml.

    Args:
        project_path: Path to the project directory

    Returns:
        List of excluded package names
    """
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
