import click
from rich_click import RichGroup

import near_py_tool.api as api
import near_py_tool.click_utils as click_utils


def do_deploy(ctx, extra_args, install_dependencies_silently=False):
    params = click_utils.all_parent_command_params(ctx)
    project_dir = params.get("deploy", {}).get("project_dir")
    rebuild_all = params.get("build-non-reproducible-wasm", {}).get("rebuild_all", False)
    install_dependencies_silently = params.get("deploy", {}).get("install_dependencies_silently", False)
    account_id = (params.get("build-non-reproducible-wasm") or params.get("build-reproducible-wasm")).get(
        "contract_account_id"
    )
    api.deploy(
        project_dir,
        rebuild_all=rebuild_all,
        account_id=account_id,
        extra_args=extra_args,
        install_dependencies_silently=install_dependencies_silently,
    )


def account_id_prompt(prompt):
    local_accounts = api.local_keychain_account_ids()
    return click_utils.choice(prompt, local_accounts) if local_accounts else click.prompt(prompt)


@click.group(cls=RichGroup, invoke_without_command=True)
@click.option("--project-dir", default=".")
@click.option("--install-dependencies-silently", is_flag=True, help="Install dependencies without asking the user")
@click.pass_context
def deploy(ctx, project_dir, install_dependencies_silently):
    """Add a new contract code"""
    click_utils.subcommand_choice(ctx)


@deploy.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument("contract_account_id")
@click.option("--rebuild-all", is_flag=True, help="Rebuild everything from scratch")
@click.argument("extra_args", nargs=-1)
def build_non_reproducible_wasm(ctx, contract_account_id, rebuild_all, extra_args):
    """Fast and simple build (recommended for use during local development)"""
    ctx.params["contract_account_id"] = (
        account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    )
    do_deploy(ctx, extra_args)


@deploy.group(cls=RichGroup, invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument("contract_account_id")
@click.argument("extra_args", nargs=-1)
def build_reproducible_wasm(ctx, contract_account_id, extra_args):
    """Build requires [reproducible_build] section in Cargo.toml, and all changes committed and pushed to git (recommended for the production release)"""
    ctx.params["contract_account_id"] = (
        account_id_prompt("Contract account ID") if not contract_account_id else contract_account_id
    )
    do_deploy(ctx, extra_args)
