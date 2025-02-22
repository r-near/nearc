import click
import questionary

default_choice_style = questionary.Style(
    [("qmark", "fg:cyan bold"), ("selected", "fg:cyan bold"), ("pointer", "fg:yellow bold")]
)


def subcommand_choice(ctx):
    if ctx.invoked_subcommand is None:
        command = ctx.command
        subcommands = [cmd for cmd in command.commands.values() if not cmd.hidden]
        if not subcommands:
            click.echo(command.help)
            ctx.exit()
        subcommand = (
            questionary.select(
                "Choose a command:",
                choices=[
                    questionary.Choice(f"{cmd.name} - {cmd.get_short_help_str()}", value=cmd) for cmd in subcommands
                ],
                style=default_choice_style,
                use_arrow_keys=True,
            ).ask()
            if len(subcommands) > 1
            else subcommands[0]
        )
        if subcommand:
            ctx.invoke(subcommand)


def choice(prompt, values):
    return questionary.select(
        prompt,
        choices=[questionary.Choice(v, value=v) for v in values],
        style=default_choice_style,
        use_arrow_keys=True,
    ).ask()


def path(prompt, values):
    return questionary.path(prompt, style=default_choice_style).ask()


def all_parent_command_params(ctx):
    cmd_params = {}
    while ctx:
        cmd_params[ctx.command.name] = ctx.params
        ctx = ctx.parent
    return cmd_params
