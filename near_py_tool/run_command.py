import sys
import os
import platform
import urllib.request
import subprocess
import shutil
import questionary
import click

from near_py_tool import click_utils

def is_platform_native_windows():
    return 'windows' in platform.system().lower() and os.environ.get('MSYSTEM', '').lower() not in {'mingw64', 'mingw32', 'msys', 'ucrt64'}
  
def is_msys2_installed(msys2_path):
    return (msys2_path / 'usr' / 'bin' / 'bash.exe').exists()
  
def msys2_run_command(msys2_path, cmd, cwd='.', check=True):
    emscripten_path = '/emsdk/upstream/emscripten'
    str_cmd = ' '.join([str(c).replace('\\', '/') for c in cmd])
    cmds = [msys2_path / 'usr' / 'bin' / 'bash.exe', '-l', '-c', 
            f"(export PATH=/ucrt64/bin:{emscripten_path}:$PATH;export MSYSTEM=UCRT64;cd {str(cwd).replace('\\', '/')};{str_cmd})"]
    click.echo(f"Running in {cwd}: {cmds}")
    exit_code = subprocess.run(cmds, cwd=cwd).returncode
    if exit_code != 0 and check:
        click.echo(click.style(f"Error: command `{' '.join(str_cmd)}` returned {exit_code}", fg='bright_red'))
        sys.exit(1)
    return exit_code
  
def install_msys2(install_path, temp_path):
    click.echo(f"install_msys2({install_path}, {temp_path})")
    try:
        shutil.rmtree(install_path)
    except Exception:
        pass
    install_path.mkdir(parents=True, exist_ok=True)
    
    msys2_url = "https://github.com/msys2/msys2-installer/releases/download/2024-12-08/msys2-x86_64-20241208.exe"
    installer_path = temp_path / "msys2_installer.exe"

    click.echo("Downloading MSYS2 installer...")
    urllib.request.urlretrieve(msys2_url, installer_path)

    click.echo("Installing MSYS2...")
    subprocess.run([str(installer_path), "install", "--root", str(install_path), "--confirm-command", "--accept-messages", "--accept-licenses"], check=True)
    
    installer_path.unlink()
    
    click.echo("Updating package databases...")
    msys2_run_command(install_path, ["pacman", "-Syu", "--noconfirm"], check=False)
    
    click.echo("Installing dependencies...")
    msys2_dependencies = ["make", "mingw-w64-ucrt-x86_64-python", "mingw-w64-ucrt-x86_64-gcc", "git", "mingw-w64-ucrt-x86_64-ca-certificates"]
    msys2_run_command(install_path, ["pacman", "-Sq", "--noconfirm"] + msys2_dependencies)
    
def get_msys2_path(build_path):
    return build_path / 'msys2'
  
def get_emsdk_path(build_path):
    return get_msys2_path(build_path) / 'emsdk' if is_platform_native_windows() else build_path / 'emsdk'
  
def install_emscripten(build_path):
    emsdk_path = get_emsdk_path(build_path)
    if not (emsdk_path / '.git').is_dir():
        run_build_command(build_path, ['git', 'clone', 'https://github.com/emscripten-core/emsdk.git'], cwd=emsdk_path.parent)
    run_build_command(build_path, ['git', 'pull'], cwd=emsdk_path)
    run_build_command(build_path, ['./emsdk', 'install', '4.0.0'], cwd=emsdk_path)
    run_build_command(build_path, ['./emsdk', 'activate', '4.0.0'], cwd=emsdk_path)
    
def check_dependencies(build_path):
    msys2_path = get_msys2_path(build_path)
    if is_platform_native_windows() and not is_msys2_installed(msys2_path):
        install_msys2(msys2_path, build_path)
        install_emscripten(build_path)
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
        # todo: command-line option to bypass any prompts
        install = click_utils.choice(
            f"Install Emscripten to {get_emsdk_path(build_path)} using the command sequence above?",
            ["Yes", "No / exit" ]).lower()
        if install == "yes":
          install_emscripten(build_path)
        else:
          sys.exit(0)
    if not is_platform_native_windows(): # don't check on native windows since we install our own msys2 there with all required packages
        if not is_command_available('make'):
            click.echo(click.style("Error: make is required for building Python NEAR contracts", fg='bright_red'))
            click.echo("Please install make via a package manager before continuing")
            sys.exit(1)
        if not is_command_available('cc'):
            click.echo(click.style("Error: cc is required for building Python NEAR contracts", fg='bright_red'))
            click.echo("Please install a C compiler via a package manager before continuing")
            sys.exit(1)

def is_command_available(command_name):
    return shutil.which(command_name) is not None

def run_command(cmd, check=True, cwd=None):
    """Runs a commmand in the host environment"""
    str_cmd = [str(c) for c in cmd]
    exit_code = subprocess.run(str_cmd, cwd=cwd).returncode
    if exit_code != 0 and check:
        click.echo(click.style(f"Error: command `{' '.join(str_cmd)}` returned {exit_code}", fg='bright_red'))
        sys.exit(1)
    return exit_code

def run_build_command(build_path, cmd, check=True, cwd=None):
    """Runs a commmand in the build environment, which can be the host or msys2 depending on the host OS"""
    return msys2_run_command(get_msys2_path(build_path), cmd, cwd=cwd, check=check) if is_platform_native_windows() else run_command(cmd, cwd=cwd, check=check)
