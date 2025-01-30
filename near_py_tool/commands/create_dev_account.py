import randomname
import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
from near_py_tool.run_command import run_command, is_command_available

def is_account_id_available(account_id, network):
    return run_command(['near', 'account', 'view-account-summary', account_id, 'network-config', network, 'now'], fail_on_nonzero_exit_code=False) != 0

def create_account(ctx, extra_args):
    if not is_command_available('near'):
        click.echo(click.style("Error: NEAR CLI is required to be installed to create a new dev account", fg='bright_red'))
        click.echo("""
You can install NEAR CLI by running one of the following commands:

  curl --proto '=https' --tlsv1.2 -LsSf https://github.com/near/near-cli-rs/releases/download/v0.18.0/near-cli-rs-installer.sh | sh
  
or 
  
  powershell -ExecutionPolicy ByPass -c "irm https://github.com/near/near-cli-rs/releases/download/v0.18.0/near-cli-rs-installer.ps1 | iex"
  
or 
  
  npm install near-cli-rs@0.18.0
  
or downloading the binaries from https://github.com/near/near-cli-rs/releases/
""")
    params = click_utils.all_parent_command_params(ctx)
    account_id = (params.get('use-random-account-id') or params.get('use-specific-account-id')).get('new_account_id')
    cmdline = ['near', 'account', 'create-account', 'sponsor-by-faucet-service', account_id]
    cmdline.extend([str(arg) for arg in extra_args])
    run_command(cmdline)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def create_dev_account(ctx):
    """Create a development account using the faucet service sponsor to receive some NEAR tokens (testnet only)"""
    click_utils.subcommand_choice(ctx)

@create_dev_account.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument("extra_args", nargs=-1)
def use_random_account_id(ctx, extra_args):
    """I would like to create a random account (useful for quick start development)"""
    new_account_id = f"{randomname.get_name()}.testnet"
    # while not is_account_id_available(new_account_id, 'testnet'):
    #   new_account_id = f"{randomname.get_name()}.testnet"
    click.echo(f"Generated account name: {new_account_id}")
    ctx.params['new_account_id'] = new_account_id
    create_account(ctx, extra_args)
    
@create_dev_account.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('new_account_id')
@click.argument("extra_args", nargs=-1)
def use_specific_account_id(ctx, new_account_id, extra_args):
    """I would like to create a specific account"""
    ctx.params['new_account_id'] = click.prompt("Account ID") if not new_account_id else new_account_id
    create_account(ctx, extra_args)
