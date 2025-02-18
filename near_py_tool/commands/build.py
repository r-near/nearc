import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
import near_py_tool.api as api

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
    api.build(project_dir, rebuild_all)

@build.command(cls=RichCommand)
@click.option('--project-dir', default='.')
@click.pass_context
def reproducible_wasm(ctx, project_dir):
    """Requires `[reproducible_build]` section in pyproject.toml, and all changes committed to git (recommended for the production release)"""
    api.build(project_dir, True)
