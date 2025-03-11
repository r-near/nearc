#!/usr/bin/env python3
"""
Build manifest generation for the NEAR Python contract compiler.
"""

import os
from pathlib import Path
from typing import Set, List, Tuple, Optional, Any

from .analyzer import is_micropython_module, MPY_STDLIB_PACKAGES
from .utils import console, find_site_packages


class ManifestGenerator:
    """Handles the generation of build manifests for NEAR Python contracts."""

    def __init__(
        self,
        contract_path: Path,
        imports: Set[str],
        exports: Set[str],
        venv_path: Path,
        build_dir: Path,
        single_file: bool = False,
    ):
        self.contract_path = contract_path
        self.imports = imports
        self.exports = exports
        self.venv_path = venv_path
        self.build_dir = build_dir
        self.contract_dir = contract_path.parent
        self.site_packages = self._get_site_packages()
        self.excluded_stdlib_packages = self._get_excluded_stdlib_packages()
        self.gitignore_spec = self._load_gitignore_spec()
        self.single_file = single_file

    def _get_site_packages(self) -> Path:
        """Get the site-packages directory from the virtual environment."""
        site_packages = find_site_packages(self.venv_path)
        if not site_packages:
            console.print(
                f"[red]Error: Could not find site-packages in {self.venv_path}"
            )
            import sys

            sys.exit(1)
        return site_packages

    def _get_excluded_stdlib_packages(self) -> List[str]:
        """Get excluded stdlib packages from pyproject.toml."""
        pyproject_path = self.contract_dir / "pyproject.toml"
        excluded_packages = []

        if pyproject_path.is_file():
            try:
                import tomllib

                with open(pyproject_path, "rb") as file:
                    pyproject_data = tomllib.load(file)
                excluded_packages = (
                    pyproject_data.get("tool", {})
                    .get("near-py-tool", {})
                    .get("exclude-micropython-stdlib-packages", [])
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not read exclusions from pyproject.toml: {e}"
                )

        if excluded_packages:
            console.print(
                f"Excluding MicroPython stdlib packages: {', '.join(excluded_packages)}"
            )

        return excluded_packages

    def _load_gitignore_spec(self) -> Optional[Any]:
        """Load gitignore patterns if available."""
        try:
            import pathspec
        except ImportError:
            console.print(
                "[yellow]pathspec library not found, gitignore filtering disabled[/]"
            )
            console.print("[yellow]Install with: pip install pathspec[/]")
            return None

        gitignore_path = self.contract_dir / ".gitignore"
        if not gitignore_path.exists():
            return None

        with open(gitignore_path, "r") as gitignore_file:
            gitignore_patterns = gitignore_file.read().splitlines()

            # Add common Python patterns if not already specified
            default_patterns = [
                "__pycache__/",
                "*.py[cod]",
                "*$py.class",
                "*.so",
                "build/",
                "dist/",
            ]
            for pattern in default_patterns:
                if pattern not in gitignore_patterns:
                    gitignore_patterns.append(pattern)

            spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern, gitignore_patterns
            )
            console.print("[cyan]Using .gitignore patterns for module filtering[/]")
            return spec

    def find_local_modules(self) -> List[Path]:
        """Find all local Python modules in the contract directory, respecting .gitignore."""
        local_modules: List[Path] = []

        # If single_file mode is enabled, skip looking for local modules
        if self.single_file:
            console.print("[cyan]Single file mode: skipping local module discovery[/]")
            return local_modules

        always_exclude = [".git", ".venv", "venv", "__pycache__", "build"]

        console.print("[cyan]Scanning for local Python modules...[/]")

        for py_file in self.contract_dir.glob("**/*.py"):
            # Skip the main contract file and generated files
            if py_file.name == self.contract_path.name or py_file.name.endswith(
                ("_with_metadata.py", "_with_abi.py")
            ):
                continue

            # Get relative path for gitignore matching
            rel_path = py_file.relative_to(self.contract_dir)
            rel_path_str = str(rel_path).replace("\\", "/")

            # Skip based on always_exclude patterns
            if any(exclude in str(py_file) for exclude in always_exclude):
                continue

            # Skip if matches gitignore patterns
            if (
                self.gitignore_spec
                and hasattr(self.gitignore_spec, "match_file")
                and self.gitignore_spec.match_file(rel_path_str)
            ):
                console.print(
                    f"  [dim yellow]Ignoring (gitignore match): {rel_path}[/]"
                )
                continue

            local_modules.append(rel_path)
            console.print(f"  [dim]Found local module: {rel_path}[/]")

        if not local_modules:
            console.print(
                "[yellow]No local modules found besides the main contract file[/]"
            )
        else:
            console.print(
                f"[green]Found {len(local_modules)} local modules to include[/]"
            )

        return local_modules

    def process_external_dependencies(
        self, local_modules: List[Path]
    ) -> List[Tuple[str, str]]:
        """Process external dependencies from imports list."""
        external_modules = {
            name.split(".")[0]
            for name in self.imports
            if not is_micropython_module(name)
        }

        external_deps = []
        missing_modules = []

        for base_module in sorted(external_modules):
            # Check if it's a local module
            local_module_file = self.contract_dir / f"{base_module}.py"
            local_module_dir = self.contract_dir / base_module
            local_module_init = local_module_dir / "__init__.py"

            if local_module_file.exists() or (
                local_module_dir.is_dir() and local_module_init.exists()
            ):
                continue  # Local module, already handled

            # Check in site-packages
            module_dir = self.site_packages / base_module
            module_file = self.site_packages / f"{base_module}.py"

            if module_dir.is_dir():
                external_deps.append((base_module, "package"))
            elif module_file.exists():
                external_deps.append((base_module, "module"))
            else:
                missing_modules.append(base_module)
                console.print(
                    f"[yellow]Warning: Could not find module {base_module} in {self.site_packages}"
                )

        return external_deps

    def write_manifest(
        self, local_modules: List[Path], external_deps: List[Tuple[str, str]]
    ) -> Path:
        """Write the manifest file."""
        manifest_path = self.build_dir / "manifest.py"

        with open(manifest_path, "w") as f:
            f.write("# THIS FILE IS GENERATED, DO NOT EDIT\n\n")

            # Add stdlib packages
            included_stdlib_packages = set(MPY_STDLIB_PACKAGES) - set(
                self.excluded_stdlib_packages
            )
            f.write(
                "\n".join(
                    f'require("{module}")'
                    for module in sorted(included_stdlib_packages)
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

            # Add local modules
            if local_modules:
                f.write("\n\n# Local modules\n")
                contract_rel_path = os.path.relpath(
                    self.contract_dir, manifest_path.parent
                ).replace("\\", "/")

                for rel_path in sorted(local_modules):
                    f.write(f'module("{rel_path}", base_path="{contract_rel_path}")\n')

            # Add external dependencies
            if external_deps:
                f.write("\n\n# External dependencies\n")
                rel_path_str = os.path.relpath(
                    self.site_packages, manifest_path.parent
                ).replace("\\", "/")

                for module_name, module_type in external_deps:
                    if module_type == "package":
                        f.write(
                            f'package("{module_name}", base_path="{rel_path_str}")\n'
                        )
                    else:
                        f.write(
                            f'module("{module_name}.py", base_path="{rel_path_str}")\n'
                        )

            # Add contract file
            f.write("\n\n# Contract\n")
            f.write(f'module("{self.contract_path.name}", base_path="..")')

        return manifest_path

    def write_wrappers(self) -> Path:
        """Generate export wrappers file."""
        wrappers_path = self.build_dir / "export_wrappers.c"

        with open(wrappers_path, "w") as f:
            f.write("/* Generated export wrappers for NEAR contract */\n\n")
            f.write(
                "void run_frozen_fn(const char *file_name, const char *fn_name);\n\n"
            )

            for export in sorted(self.exports):
                f.write(f"void {export}() {{\n")
                f.write(
                    f'    run_frozen_fn("{self.contract_path.name}", "{export}");\n'
                )
                f.write("}\n\n")

        return wrappers_path

    def generate(self) -> Tuple[Path, Path]:
        """Generate all build files."""
        local_modules = self.find_local_modules()
        external_deps = self.process_external_dependencies(local_modules)

        console.print("[cyan]Generating build files...[/]", end="")
        manifest_path = self.write_manifest(local_modules, external_deps)
        wrappers_path = self.write_wrappers()
        console.print(" done")

        return manifest_path, wrappers_path


def prepare_build_files(
    contract_path: Path,
    imports: Set[str],
    exports: Set[str],
    venv_path: Path,
    build_dir: Path,
    single_file: bool = False,
) -> Tuple[Path, Path]:
    """
    Generate manifest and wrapper files for NEAR contract compilation.

    Args:
        contract_path: Path to the contract file
        imports: Set of imported module names
        exports: Set of exported function names
        venv_path: Path to the virtual environment
        build_dir: Path to the build directory
        single_file: Whether to skip local module discovery and compile only the specified file

    Returns:
        Tuple of (manifest_path, wrappers_path)
    """
    generator = ManifestGenerator(
        contract_path, imports, exports, venv_path, build_dir, single_file
    )
    return generator.generate()
