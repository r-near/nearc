import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
from pathlib import Path
import json
from near_py_tool.run_command import run_command, is_command_available
from near_py_tool.commands.build import do_build

# todo: decide what to do with extra cmdline arguments inherited form cargo-near which aren't available in near-cli-rs which we are calling to here

def do_deploy(ctx, extra_args):
    if not is_command_available('near'):
        click.echo(click.style("Error: NEAR CLI is required to be installed to deploy a contract", fg='bright_red'))
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
    project_dir = params.get('deploy', {}).get('project_dir')
    rebuid_all = params.get('build-non-reproducible-wasm', {}).get('rebuild_all', False)
    project_path = Path(project_dir).resolve()
    project_name = project_path.name
    
    wasm_path = project_path / "build" / Path(project_name).with_suffix(".wasm")    
    do_build(project_path, rebuid_all)

    account_id = (params.get('build-non-reproducible-wasm') or params.get('build-reproducible-wasm')).get('contract_account_id')
    if account_id == '*':
      account_id = local_keychain_account_ids()[0]
    
    cmdline = ['near', 'contract', 'deploy', account_id, 'use-file', wasm_path]
    cmdline.extend([str(arg) for arg in extra_args])
    
    run_command(cmdline, cwd=project_path)
    
def local_keychain_account_ids():
    try:
        accounts_path = Path("~/.near-credentials/accounts.json").expanduser().resolve()
        with open(accounts_path, "r") as f:
            d = json.load(f)
            return [v['account_id'] for v in d]
    except:
        pass
  
def account_id_prompt(prompt):
    local_accounts = local_keychain_account_ids()
    return click_utils.choice(prompt, local_accounts) if local_accounts else click.prompt(prompt)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.option('--project-dir', default='.')
@click.pass_context
def deploy(ctx, project_dir):
    """Add a new contract code"""
    click_utils.subcommand_choice(ctx)
    
@deploy.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('contract_account_id')
@click.option('--rebuild-all', is_flag=True, help="Rebuild everything from scratch")
@click.argument("extra_args", nargs=-1)
def build_non_reproducible_wasm(ctx, contract_account_id, rebuild_all, extra_args):
    """Fast and simple build (recommended for use during local development)"""
    ctx.params['contract_account_id'] = account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    do_deploy(ctx, extra_args)

@deploy.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('contract_account_id')
@click.argument("extra_args", nargs=-1)
def build_reproducible_wasm(ctx, contract_account_id, extra_args):
    """Build requires [reproducible_build] section in Cargo.toml, and all changes committed and pushed to git (recommended for the production release)"""
    ctx.params['contract_account_id'] = account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    do_deploy(ctx, extra_args)
