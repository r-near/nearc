import sys
import subprocess
import shutil
import click

def is_command_available(command_name):
    return shutil.which(command_name) is not None

def run_command(cmd, fail_on_nonzero_exit_code=True, cwd=None):
    str_cmd = [str(c) for c in cmd]
    exit_code = subprocess.run(str_cmd, cwd=cwd).returncode
    if exit_code != 0 and fail_on_nonzero_exit_code:
        click.echo(click.style(f"Error: command `{' '.join(str_cmd)}` returned {exit_code}", fg='bright_red'))
        sys.exit(1)
    return exit_code
