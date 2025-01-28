import randomname
import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
from near_py_tool.run_command import run_command, is_command_available

def is_account_id_available(account_id, network):
    return run_command(['near', 'account', 'view-account-summary', account_id, 'network-config', network, 'now'], fail_on_nonzero_exit_code=False) != 0

def create_account(ctx, network):
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
    if 'autogenerate-new-keypair' in params:
        cmdline.append('autogenerate-new-keypair')
    elif 'use-manually-provided-seed-phrase' in params:
        cmdline.append('use-manually-provided-seed-phrase')
        cmdline.append(params.get('use-manually-provided-seed-phrase', {}).get('master_seed_phrase'))
    elif 'use-manually-provided-public-key' in params:
        cmdline.append('use-manually-provided-public-key')
        cmdline.append(params.get('use-manually-provided-public-key', {}).get('public_key'))
    elif 'use-ledger' in params:
        cmdline.append('use-ledger')
        cmdline.append(params.get('use-ledger', {}).get('seed_phrase_hd_path'))
    for cmd in ['save-to-keychain', 'save-to-legacy-keychain', 'print-to-terminal']:
        if cmd in params:
            cmdline.append(cmd)
    cmdline.append('network-config')
    cmdline.append(network)
    cmdline.append('create')
    run_command(cmdline)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def create_dev_account(ctx):
    """Create a development account using the faucet service sponsor to receive some NEAR tokens (testnet only)"""
    click_utils.subcommand_choice(ctx)

@create_dev_account.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def use_random_account_id(ctx):
    """I would like to create a random account (useful for quick start development)"""
    new_account_id = f"{randomname.get_name()}.testnet"
    # while not is_account_id_available(new_account_id, 'testnet'):
    #   new_account_id = f"{randomname.get_name()}.testnet"
    click.echo(f"Generated account name: {new_account_id}")
    ctx.params['new_account_id'] = new_account_id
    click_utils.subcommand_choice(ctx)
    
@create_dev_account.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.argument('new_account_id')
def use_specific_account_id(ctx, new_account_id):
    """I would like to create a specific account"""
    ctx.params['new_account_id'] = click.prompt("Account ID") if not new_account_id else new_account_id
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def autogenerate_new_keypair(ctx):
    """Automatically generate a key pair"""
    click_utils.subcommand_choice(ctx)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.argument('master_seed_phrase')
@click.pass_context
def use_manually_provided_seed_phrase(ctx, master_seed_phrase):
    """Use the provided seed phrase manually"""
    ctx.params['master_seed_phrase'] = click.prompt("Enter the seed-phrase for this account") if not master_seed_phrase else master_seed_phrase
    click_utils.subcommand_choice(ctx)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.argument('public_key')
@click.pass_context
def use_manually_provided_public_key(ctx, public_key):
    """Use the provided public key manually"""
    ctx.params['public_key'] = click.prompt("Enter the public key for this account") if not public_key else public_key
    click_utils.subcommand_choice(ctx)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.argument('seed_phrase_hd_path')
@click.pass_context
def use_ledger(ctx, seed_phrase_hd_path):
    """Use a ledger"""
    ctx.params['seed_phrase_hd_path'] = click.prompt("Enter seed phrase HD Path (if you not sure leave blank for default)") if not seed_phrase_hd_path else seed_phrase_hd_path
    click_utils.subcommand_choice(ctx)
  
for cmd in [autogenerate_new_keypair, use_manually_provided_seed_phrase, use_manually_provided_public_key, use_ledger]:
    for group in [use_random_account_id, use_specific_account_id]:
        group.add_command(cmd)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def save_to_keychain(ctx):
    """Save automatically generated key pair to keychain"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def save_to_legacy_keychain(ctx):
    """Save automatically generated key pair to the legacy keychain (compatible with JS CLI)"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def print_to_terminal(ctx):
    """Print automatically generated key pair in terminal"""
    click_utils.subcommand_choice(ctx)

for cmd in [save_to_keychain, save_to_legacy_keychain, print_to_terminal]:
    for group in [autogenerate_new_keypair, use_manually_provided_seed_phrase, use_manually_provided_public_key, use_ledger]:
        group.add_command(cmd)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def network_config(ctx):
    """What is the name of the network?"""
    click_utils.subcommand_choice(ctx)

for cmd in [network_config]:
    for group in [save_to_keychain, save_to_legacy_keychain, print_to_terminal]:
        group.add_command(cmd)
    
@network_config.group(cls=RichGroup, invoke_without_command=True)
@click.argument('create')
@click.pass_context
def testnet(ctx, create):
    create_account(ctx, 'testnet')

@network_config.group(cls=RichGroup, invoke_without_command=True)
@click.argument('create')
@click.pass_context
def mainnet(ctx, create):
    create_account(ctx, 'mainnet')
