import click
from rich_click import RichGroup, RichCommand
import near_py_tool.click_utils as click_utils
from pathlib import Path
import json
from near_py_tool.run_command import run_command, is_command_available
from near_py_tool.commands.build import do_build

# todo: decide what to do with extra cmdline arguments inherited form cargo-near which aren't available in near-cli-rs which we are calling to here

def do_deploy(ctx):
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
    account_id = (params.get('build-non-reproducible-wasm') or params.get('build-non-reproducible-wasm')).get('contract_account_id')
    project_dir = Path(".")
    # project_dir = Path("../test-project-1")
    project_path = Path(project_dir).resolve()
    project_name = project_path.name
    
    wasm_path = project_path / "build" / Path(project_name).with_suffix(".wasm")
    
    do_build(project_path, False)

    network = 'mainnet' if 'mainnet' in params else 'testnet'
    cmdline = ['near', 'deploy', account_id, wasm_path, '--network-id', network]
    if 'with-init-call' in params:
        cmdline.extend(['--init-function', params.get('with-init-call', {}).get('function_name'),
                        '--init-args', params.get('with-init-call', {}).get('function_args')])
    if 'prepaid-gas' in params:
        cmdline.extend(['--init-gas', params.get('prepaid-gas', {}).get('gas')])
    if 'attached-deposit' in params:
        cmdline.extend(['--init-deposit', params.get('attached-deposit', {}).get('deposit')])
    
    run_command(cmdline)

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
@click.pass_context
def deploy(ctx):
    """Add a new contract code"""
    click_utils.subcommand_choice(ctx)
    
@deploy.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.argument('contract_account_id')
@click.option('--locked', is_flag=True)
@click.option('--no-release', is_flag=True)
@click.option('--no-abi', is_flag=True)
@click.option('--no-embed-abi', is_flag=True)
@click.option('--no-doc', is_flag=True)
@click.option('--no-wasmopt', is_flag=True)
@click.option('--out-dir', metavar='<OUT_DIR>')
@click.option('--manifest-path', metavar='<MANIFEST_PATH>')
@click.option('--features', metavar='<FEATURES>')
@click.option('--no-default-features', is_flag=True)
@click.option('--rebuild-all', is_flag=True, help="Rebuild everything from scratch")
def build_non_reproducible_wasm(ctx, contract_account_id, **kwarg):
    #locked, no_release, no_abi, no_embed_api, no_doc, no_wasmopt, out_dir, manifest_path, featured, no_default_features
    """Fast and simple build (recommended for use during local development)"""
    ctx.params['contract_account_id'] = account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    click_utils.subcommand_choice(ctx)

@deploy.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.argument('contract_account_id')
@click.option('--no-locked', is_flag=True)
@click.option('--out-dir', metavar='<OUT_DIR>')
@click.option('--manifest-path', metavar='<MANIFEST_PATH>')
@click.option('--skip-git-remote-check', is_flag=True)
def build_reproducible_wasm(ctx, contract_account_id, **kwarg):
    """Build requires [reproducible_build] section in Cargo.toml, and all changes committed and pushed to git (recommended for the production release)"""
    ctx.params['contract_account_id'] = account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.argument('function_name')
@click.argument('function_args_type', type=click.Choice(['json-args', 'text-args', 'base64-args', 'file-args'], case_sensitive=False))
@click.argument('function_args')
@click.pass_context
def with_init_call(ctx, function_name, function_args_type, function_args):
    """Add an initialize"""
    ctx.params['function_name'] = click.prompt("Function name") if not function_name else function_name
    ctx.params['function_args_type'] = click_utils.choice("Function args type", ['json-args', 'text-args', 'base64-args', 'file-args']) if not function_args_type else function_args_type
    ctx.params['function_args'] = click.prompt("Function args") if not function_args else function_args
    click_utils.subcommand_choice(ctx)

@with_init_call.group(cls=RichGroup, invoke_without_command=True)
@click.argument('gas')
@click.pass_context
def prepaid_gas(ctx, gas):
    """Enter gas for function call"""
    ctx.params['gas'] = click.prompt("Gas", default=30000000000000) if not gas else gas
    click_utils.subcommand_choice(ctx)

@prepaid_gas.group(cls=RichGroup, invoke_without_command=True)
@click.argument('deposit', default=0)
@click.pass_context
def attached_deposit(ctx, deposit):
    """Enter deposit for a function call"""
    ctx.params['deposit'] = click.prompt("Deposit", default=0) if not deposit else deposit
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def without_init_call(ctx):
    """Don't add an initialize"""
    click_utils.subcommand_choice(ctx)

for cmd in [with_init_call, without_init_call]:
    for group in [build_non_reproducible_wasm, build_reproducible_wasm]:
        group.add_command(cmd)
    
@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def network_config(ctx):
    """What is the name of the network?"""
    click_utils.subcommand_choice(ctx)

@network_config.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def testnet(ctx):
  click_utils.subcommand_choice(ctx)
    
@network_config.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def mainnet(ctx):
  click_utils.subcommand_choice(ctx)
  
for cmd in [network_config]:
    for group in [attached_deposit, without_init_call]:
        group.add_command(cmd)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--signer-public-key', metavar='<SIGNER_PUBLIC_KEY>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_keychain(ctx, **kwarg):
    """Sign the transaction with a key saved in keychain"""
    # ctx.params['signer_public_key'] = click.prompt("Signer public key") if not kwarg['signer_public_key'] else kwarg['signer_public_key']
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--signer-public-key', metavar='<SIGNER_PUBLIC_KEY>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_legacy_keychain(ctx, **kwarg):
    """Sign the transaction with a key saved in legacy keychain (compatible with the old near CLI)"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--seed-phrase-hd-path', metavar='<SEED_PHRASE_HD_PATH>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_ledger(ctx, **kwarg):
    """Sign the transaction with Ledger Nano device"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--signer-public-key', metavar='<SIGNER_PUBLIC_KEY>', prompt=True)
@click.option('--signer-private-key', metavar='<SIGNER_PRIVATE_KEY>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_plaintext_private_key(ctx, **kwarg):
    """Sign the transaction with a plaintext private key"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.argument('file_path')
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_access_key_file(ctx, file_path, **kwarg):
    """Sign the transaction using the account access key file (access_key_file.json)"""
    ctx.params['file_path'] = click.prompt("Function name") if not file_path else file_path
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--seed-phrase-hd-path', metavar='<SEED_PHRASE_HD_PATH>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
@click.option('--block-height', metavar='<BLOCK_HEIGHT>')
@click.option('--meta-transaction-valid-for', metavar='<META_TRANSACTION_VALID_FOR>')
def sign_with_seed_phrase(ctx, **kwarg):
    """Sign the transaction using the seed phrase"""
    click_utils.subcommand_choice(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.option('--signer-public-key', metavar='<SIGNER_PUBLIC_KEY>', prompt=True)
@click.option('--nonce', metavar='<NONCE>')
@click.option('--block-hash', metavar='<BLOCK_HASH>')
def sign_later(ctx, **kwarg):
    """Prepare unsigned transaction to sign it later"""
    click_utils.subcommand_choice(ctx)

for cmd in [sign_with_keychain, sign_with_legacy_keychain, sign_with_ledger, sign_with_plaintext_private_key, 
            sign_with_access_key_file, sign_with_seed_phrase, sign_later]:
    for group in [testnet, mainnet]:
        group.add_command(cmd)
  
@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def send(ctx):
    """Send the transaction to the network"""
    do_deploy(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
@click.argument('file_path')
def save_to_file(ctx, file_path):
    """Save the signed transaction to file (if you want to send it later)"""
    ctx.params['file_path'] = click.prompt("Save to file path") if not file_path else file_path
    do_deploy(ctx)

@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def display(ctx):
    """Print the signed transaction to terminal (if you want to send it later)"""
    do_deploy(ctx)

for cmd in [send, save_to_file, display]:
    for group in [sign_with_keychain, sign_with_legacy_keychain, sign_with_ledger, sign_with_plaintext_private_key, 
                  sign_with_access_key_file, sign_with_seed_phrase]:
        group.add_command(cmd)

for cmd in [save_to_file, display]:
    for group in [sign_later]:
        group.add_command(cmd)
