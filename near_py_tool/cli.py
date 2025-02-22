import click
from rich_click import RichGroup

import near_py_tool.click_utils as click_utils
from near_py_tool.commands.abi import abi
from near_py_tool.commands.build import build
from near_py_tool.commands.create_dev_account import create_dev_account
from near_py_tool.commands.deploy import deploy
from near_py_tool.commands.new import new


@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Python NEAR contract build/deploy tool"""
    click_utils.subcommand_choice(ctx)


cli.add_command(new)
cli.add_command(build)
cli.add_command(abi)
cli.add_command(create_dev_account)
cli.add_command(deploy)

if __name__ == "__main__":
    cli(None)
