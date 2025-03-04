#!/usr/bin/env python3
"""
Utility functions for the NEAR Python contract compiler.
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Callable, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TaskID

# Global console instance for printing messages
console = Console()


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
