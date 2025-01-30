import ast
import os
import sys
import shutil
from pathlib import Path
from importlib.resources import files
import toml
import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
from near_py_tool.run_command import run_command, is_command_available

def get_near_exports_from_file(file_path):
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    near_exports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Name) and d.attr == 'export' and d.value.id == 'near':
                    near_exports.add(node.name)
        if isinstance(node, ast.FunctionDef) and any(isinstance(d, ast.Name) and d.id == 'near.export' for d in node.decorator_list):
            near_exports.add(node.name)

    return near_exports

def get_imports_from_file(file_path):
    """Extract imported modules from a Python file."""
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module:
                imports.add(module)

    return imports

def has_compiled_extensions(package_name, package_path):
    native_library_paths = []
    for ext in ["so", "pyd", "dll", "dylib"]:
        native_library_paths.append(package_path.rglob(f"*.{ext}"))
    return len(native_library_paths) == 0   

def is_mpy_module(name):
    mpy_modules = [
        'array', 'builtins', 'json', 'os', 'random', 'struct', 'sys'
    ]
    return name in mpy_modules

def is_mpy_lib_package(name):
    mpy_lib_packages = [
        'aiohttp', 'cbor2', 'iperf3', 'pyjwt', 'requests'
    ]
    return name in mpy_lib_packages

mpy_stdlib_packages = [
    'binascii', 'contextlib', 'fnmatch', 'hashlib-sha224', 'hmac', 'keyword', 'os-path', 'pprint', 
    'stat', 'tempfile', 'types', 'warnings', '__future__', 'bisect', 'copy', 'functools', 'hashlib-sha256', 
    'html', 'locale', 'pathlib', 'quopri', 'string', 'textwrap', 'unittest', 'zlib', 'abc', 'cmd', 'curses.ascii', 
    'gzip', 'hashlib-sha384', 'inspect', 'logging', 'pickle', 'random', 'struct', 'threading', 'unittest-discover',
    'argparse', 'collections', 'datetime', 'hashlib', 'hashlib-sha512', 'io', 'operator', 'pkg_resources', 'shutil', 
    'tarfile', 'time', 'uu', 'base64', 'collections-defaultdict', 'errno', 'hashlib-core', 'heapq', 'itertools', 'os', 
    'pkgutil', 'ssl', 'tarfile-write', 'traceback', 'venv'
]

near_module_name = 'near'

def is_external_package(name):
    return not is_mpy_module(name) and not is_mpy_lib_package(name) and name not in mpy_stdlib_packages and name != near_module_name

def generate_manifest(contract_path, package_paths, manifest_path):
    with open(manifest_path, "w") as o:
        o.write("# THIS FILE IS GENERATED, DO NOT EDIT\n\n")
        for module in mpy_stdlib_packages:
            o.write(f'require("{module}")\n')
        for mod in ["typing", "typing_extensions"]:
            o.write(f'module("{mod}.py", base_path="$(PORT_DIR)/extra/typing")\n')
        for module, path in package_paths.items():
            if is_mpy_lib_package(module):
                o.write(f'require("{module}")\n')
            elif not is_mpy_module(module):
                o.write(f'package("{module}", base_path="{path.parent}")\n')
        o.write(f'module("{contract_path.name}", base_path="{contract_path.parent}")\n')

def generate_export_wrappers(contract_path, exports, export_wrappers_path):
    with open(export_wrappers_path, "w") as o:
        o.write("/* THIS FILE IS GENERATED, DO NOT EDIT */\n\n")
        o.write("void run_frozen_fn(const char *file_name, const char *fn_name);\n\n")
        for export in exports:
            o.write(f'void {export}() \u007b\n  run_frozen_fn("{contract_path.name}", "{export}");\n\u007d\n\n');

def get_venv_package_paths(file_path, venv_path):
    """Get paths of all packages imported by a Python file."""
    imports = get_imports_from_file(file_path)
    package_paths = {}
    glob_pattern_base = "lib/site-packages" if (venv_path / 'lib' / 'site-packages').is_dir() else "lib/python*.*/site-packages"
    for module_name in imports:
        if is_external_package(module_name):
          paths = list(venv_path.glob(f"{glob_pattern_base}/{module_name}"))
          if len(paths) == 0:
              click.echo(f"Warning: module {module_name} path wasn't resolved; is it installed in the current venv at {venv_path}?")
          elif len(paths) > 1:
              click.echo(f"Warning: module {module_name} has multiple candidate paths: {paths}")
          for path in paths:
              package_paths[module_name] = path

    return package_paths

def install_pyproject_dependencies(project_path, venv_path):
    with open(project_path / "pyproject.toml", "r") as file:
        pyproject_data = toml.load(file)
    for package in pyproject_data.get("project", {}).get("dependencies", {}):
        click.echo(f"Installing {package} into {venv_path}...")
        pip_path = venv_path / "bin" / "pip"
        if not pip_path.is_file():
            pip_path = venv_path / "Scripts" / "pip.exe"
            if not pip_path.is_file():
                click.echo(click.style(f"Error: build Python venv doesn't have pip installed", fg='bright_red'))
                sys.exit(1)
        run_command([pip_path, "install", package, "--disable-pip-version-check"], cwd=project_path)

def do_build(project_dir, rebuild_all):
    project_path = Path(project_dir).resolve()
    print(f"project_path: {project_path}")
    project_name = project_path.name
    build_path = project_path / "build"
    mpy_cross_build_path = project_path / "build" / "mpy-cross"
    venv_path = build_path / ".venv"
    mpy_cross_path = files("near_py_tool") / "assets" / "micropython" / "mpy-cross"
    mpy_port_path = files("near_py_tool") / "assets" / "micropython" / "ports" / "webassembly-near"
    contract_path = project_path / "contract.py"
    if not contract_path.is_file():
        click.echo(click.style(f"Error: contract file {contract_path} doesn't exist", fg='bright_red'))
        sys.exit(1)
        
    if not is_command_available('emcc'):
        click.echo(click.style("Error: Emscripten C to WASM compiler is required for building Python NEAR contracts", fg='bright_red'))
        click.echo("""
You can install Emscripten via a package manager or by doing the following:

  git clone https://github.com/emscripten-core/emsdk.git
  cd emsdk
  ./emsdk install latest
  ./emsdk activate latest
  source ./emsdk_env.sh
                               
""")
        sys.exit(1)

    if not is_command_available('make'):
        click.echo(click.style("Error: make is required for building Python NEAR contracts", fg='bright_red'))
        click.echo("Please install make via a package manager before continuing")
        sys.exit(1)
    
    if rebuild_all:
        click.echo(f"Removing build directory {build_path} to perform a clean build")
        try:
            shutil.rmtree(build_path)
        except Exception:
            pass

    build_path.mkdir(parents=True, exist_ok=True)

    # todo: check for uv and emcc presence and offer installation if missing 
    # https://emscripten.org/docs/getting_started/downloads.html

    # click.echo(f"Running `uv sync` in {project_path}...")
    # run_command(['uv', "sync"], cwd=project_path)

    if not venv_path.is_dir():
        click.echo(f"Creating a venv in {venv_path}...")
        run_command(['python' if is_command_available('python') else 'python3', "-m", "venv", venv_path], cwd=project_path)
      
    install_pyproject_dependencies(project_path, venv_path)

    package_paths = get_venv_package_paths(contract_path, venv_path)

    for module, path in package_paths.items():
        if has_compiled_extensions(module, path):
            click.echo(click.style(f"Warning: required module {module} at {path} has compiled extensions and might not work correctly in WASM environment", fg="bright_red"))

    exports = list(get_near_exports_from_file(contract_path))
    click.echo(f"The contract WASM will export the following methods: {exports}")

    generate_manifest(contract_path, package_paths, build_path / "manifest.py")
    generate_export_wrappers(contract_path, exports, build_path / "export_wrappers.c")
    try:
        os.unlink(build_path / 'frozen_content.c')  # force frozen content rebuilt every time
    except Exception:
        pass

    contract_wasm_path = build_path / Path(project_name).with_suffix(".wasm")
    
    run_command(['make', "-C", mpy_cross_path,
                 f"BUILD={mpy_cross_build_path}"],
                cwd=project_path)

    run_command(['make', "-C", mpy_port_path,
                 f"BUILD={build_path}",
                 f"MICROPY_MPYCROSS={mpy_cross_build_path}/mpy-cross",
                 f"MICROPY_MPYCROSS_DEPENDENCY={mpy_cross_build_path}/mpy-cross",
                 f"FROZEN_MANIFEST={build_path / 'manifest.py'}",
                 f"SRC_C_GENERATED={build_path / 'export_wrappers.c'}",
                 f"EXPORTED_FUNCTIONS={','.join(['_' + e for e in exports])}",
                 f"OUTPUT_WASM={contract_wasm_path}"],
                cwd=project_path)
             
    click.echo(f"Contract WASM file was build successfully and is located at {contract_wasm_path}")

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def build(ctx):
    """Build a NEAR contract with embedded ABI"""
    click_utils.subcommand_choice(ctx)

@build.command(cls=RichCommand)
@click.option('--project-dir', default='.')
@click.option('--rebuild-all', is_flag=True, help="Rebuild everything from scratch")
@click.pass_context
def non_reproducible_wasm(ctx, project_dir, rebuild_all):
    """Fast and simple (recommended for use during local development)"""
    do_build(project_dir, rebuild_all)

@build.command(cls=RichCommand)
@click.option('--project-dir', default='.')
@click.pass_context
def reproducible_wasm(ctx, project_dir):
    """Requires `[reproducible_build]` section in pyproject.toml, and all changes committed to git (recommended for the production release)"""
    do_build(project_dir, True)
