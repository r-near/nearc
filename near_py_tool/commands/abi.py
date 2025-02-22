import click
from rich_click import RichCommand


@click.command(cls=RichCommand)
@click.option("--locked", is_flag=True)
@click.option("--no-doc", is_flag=True)
@click.option("--compact-abi", is_flag=True)
@click.option("--out-dir", metavar="<OUT_DIR>")
@click.option("--manifest-path", metavar="<MANIFEST_PATH>")
def abi(locked, no_doc, compact_abi, out_dir, manifest_path):
    """Generates ABI for the contract"""
    pass
