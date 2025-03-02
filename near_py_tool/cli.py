import click
import os
import sys
from pathlib import Path

from near_py_tool.api import build


@click.group()
@click.version_option()
def cli():
    """NEAR Python Tool - Build and deploy Python contracts to the NEAR blockchain."""
    pass


@cli.command()
@click.argument('project_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
@click.option('--contract', '-c', 'contract_name', default='contract.py', help='Contract file name')
@click.option('--rebuild-all', is_flag=True, help='Force rebuilding all dependencies')
def build_contract(project_dir, contract_name, rebuild_all):
    """Build a NEAR Python contract."""
    try:
        output_path = build(
            project_dir=project_dir,
            rebuild_all=rebuild_all,
            contract_name=contract_name
        )
        click.echo(f"Contract built successfully at: {output_path}")
    except Exception as e:
        click.echo(click.style(f"Error during build: {str(e)}", fg="bright_red"))
        sys.exit(1)


if __name__ == '__main__':
    cli()