import os
import shutil
from importlib.resources import files
from pathlib import Path

import click
import toml
from rich_click import RichCommand

import near_py_tool.click_utils as click_utils


@click.command(cls=RichCommand)
@click.argument("project_dir", default="")
@click.pass_context
def new(ctx, project_dir):
    """Initializes a new project to create a contract"""
    project_dir = click.prompt("Project directory") if project_dir == "" else project_dir

    new_project_template = files("near_py_tool") / "assets" / "new-project-template"
    project_abs_path = Path(project_dir).resolve()

    if os.path.isdir(project_abs_path):
        click.echo("Error:")
        click.echo(
            click.style(
                f"   Destination `{project_abs_path}` already exists. Refusing to overwrite existing project.",
                fg="bright_red",
            )
        )
        return

    project_abs_path.mkdir(parents=True, exist_ok=True)
    for src_item in new_project_template.iterdir():
        dst_item = project_abs_path / src_item.name
        if src_item.is_dir():
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)

    pyproject = toml.load(new_project_template / "pyproject.toml")
    pyproject["project"]["name"] = project_abs_path.name
    with open(project_abs_path / "pyproject.toml", "w") as f:
        toml.dump(pyproject, f)

    click.echo(
        f"""
New project is created at '{project_abs_path}'.

Now you can build, test, and deploy your project using near-py-tool:
 * `near-py-tool build`
 * `near-py-tool deploy`
"""
    )


# Your new project has preconfigured automations for CI and CD, just configure `NEAR_CONTRACT_STAGING_*` and `NEAR_CONTRACT_PRODUCTION_*` variables and secrets on GitHub to enable automatic deployment to staging and production. See more details in `.github/workflow/*` files.
# """)
