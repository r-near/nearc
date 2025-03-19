#!/usr/bin/env python3
"""
Utility functions for the NEAR Python contract compiler.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn

# Global console instance for printing messages
console = Console()


def is_running_in_container() -> bool:
    """
    Detect if we're running inside a container.

    Returns:
        True if running in a container, False otherwise
    """
    # Common indicators for Docker/Podman containers
    # 1. Check for /.dockerenv file
    if Path("/.dockerenv").exists():
        return True

    # 2. Check cgroup
    try:
        with open("/proc/1/cgroup", "r") as f:
            if "docker" in f.read() or "podman" in f.read():
                return True
    except (FileNotFoundError, IOError):
        pass

    # 3. Check container environment variables
    if os.environ.get("CONTAINER", "") or os.environ.get("PODMAN_CONTAINER", ""):
        return True

    return False


def setup_venv(venv_path: Path, project_dir: Path) -> bool:
    """
    Set up a virtual environment and install dependencies.

    Args:
        venv_path: Path to the virtual environment
        project_dir: Path to the project directory with pyproject.toml

    Returns:
        True if successful, False otherwise
    """
    console.print(f"[cyan]Setting up virtual environment at {venv_path}...[/]")

    # First, try to use uv if available
    if shutil.which("uv"):
        # Install dependencies with uv
        if not run_command_with_progress(
            ["uv", "sync"],
            cwd=project_dir,
            description="Installing dependencies with uv",
        ):
            console.print("[red]Failed to install dependencies with uv")
            return False
    else:
        # Fallback to standard pip-based workflow
        # Create venv
        if not run_command_with_progress(
            [sys.executable, "-m", "venv", str(venv_path)],
            cwd=project_dir,
            description="Creating virtual environment",
        ):
            console.print("[red]Failed to create virtual environment")
            return False

        # Install pip requirements using pyproject.toml
        pip_executable = venv_path / "bin" / "pip"
        if not pip_executable.exists():
            pip_executable = venv_path / "Scripts" / "pip.exe"  # Windows path

        if not run_command_with_progress(
            [str(pip_executable), "install", "-e", "."],
            cwd=project_dir,
            description="Installing dependencies",
        ):
            console.print("[red]Failed to install dependencies")
            return False

    console.print("[green]Virtual environment setup complete[/]")
    return True


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
