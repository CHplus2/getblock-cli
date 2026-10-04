"""Literal terminal presentation; machine output never enters this module."""
from contextlib import nullcontext
import os
import sys
import typer
from rich.console import Console
from rich.text import Text


def console(stderr=False):
    from getblock.ux import current
    state = current.get()
    mode = getattr(state, 'color', 'auto')
    machine = getattr(state, 'output', 'table') != 'table'
    disabled = machine or mode == 'never' or 'NO_COLOR' in os.environ
    return Console(file=sys.stderr if stderr else sys.stdout, force_terminal=False if disabled else (True if mode == 'always' else None), no_color=disabled, color_system="standard" if mode == "always" and not disabled else "auto", legacy_windows=False, markup=False, highlight=False)


def say(message, *, style=None, err=False):
    from getblock.output import safe_text
    target = console(err)
    message = safe_text(message)
    if not target.is_terminal:
        typer.echo(message, err=err)
    else:
        target.print(Text(message, style=style or ''), soft_wrap=True)


def waiting():
    from getblock.ux import current
    state = current.get()
    if not sys.stderr.isatty() or getattr(state, 'output', 'table') != 'table':
        return nullcontext()
    return console(True).status(Text('Waiting for GetBlock…'), spinner='dots')
