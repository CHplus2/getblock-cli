"""Terminal navigation over existing read-only Public API operations."""
import copy
import os
import shlex

import typer

from getblock import ux
from getblock.http_client import GetBlockAPIError
from getblock.output import render, safe_text
from getblock.workflows import choose


class Navigate(Exception):
    def __init__(self, destination):
        self.destination = destination


def menu(title, options):
    selection = choose(title, options)
    if selection in ("Home", "Exit"):
        raise Navigate(selection)
    return selection


def show_command(*arguments):
    state = ux.current.get()
    args = ["getblock"]
    if state.profile != "default":
        args += ["--profile", state.profile]
    args += list(arguments)
    # Display only; never execute a shell or include credentials.
    def quote(value):
        value = ux.clean(value)
        if os.name == "nt":
            return "'" + value.replace("'", "''") + "'" if any(c.isspace() or c in "'\";$`&|()<>" for c in value) else value
        return shlex.quote(value)
    typer.echo("Command: " + " ".join(quote(arg) for arg in args), err=True)


def show(data):
    render(data, output="table")


def browse(resource, inspect=False):
    from getblock import cli
    client = cli.get_authenticated_client()
    listing = client.get_protocols if resource == "protocols" else client.get_tokens
    details = client.get_protocol if resource == "protocols" else client.get_token
    offset = 0
    while True:
        show_command(resource, "list", "--limit", "20", "--offset", str(offset))
        data = listing(limit=20, offset=offset)
        if not isinstance(data, dict) or not isinstance(data.get(resource), list):
            raise ux.CLIError("The API returned an unexpected collection response.")
        rows = data[resource]
        show(data)
        # Labels map to the original ID without parsing or normalizing it.
        choices = {}
        if inspect:
            for index, row in enumerate(rows, 1):
                if isinstance(row, dict) and isinstance(row.get("id"), str):
                    label = f"{index}: {safe_text(row.get('name') or row['id'])} ({safe_text(row['id'])})"
                    choices[label] = row['id']
        total = data.get("total")
        more = bool(rows) and (not isinstance(total, int) or offset + len(rows) < total)
        options = list(choices)
        if more:
            options.append("Next page")
        if offset:
            options.append("First page")
        options += ["Back", "Home", "Exit"]
        selected = menu("Select a resource" if inspect else "Page navigation", options)
        if selected == "Back":
            return
        if selected == "Next page":
            offset += len(rows)
        elif selected == "First page":
            offset = 0
        else:
            identifier = choices[selected]
            show_command(resource, "get", identifier)
            show(details(identifier))
            if menu("After details", ["Back", "Home", "Exit"]) == "Back":
                continue


def section(name):
    from getblock import cli
    actions = ["Show account", "View balance", "View subscription"] if name == "Account" else ["List", "Inspect"]
    while True:
        action = menu(name, actions + ["Back", "Home", "Exit"])
        if action == "Back":
            return
        try:
            if name == "Account":
                methods = {"Show account": ("show", "get_me"), "View balance": ("balance", "get_balance"), "View subscription": ("plan", "get_subscription")}
                command, method = methods[action]
                show_command("account", command)
                show(getattr(cli.get_authenticated_client(), method)())
            else:
                browse(name.lower(), inspect=action == "Inspect")
        except (ux.CLIError, GetBlockAPIError) as error:
            ux.report(error, ux.current.get())
            # A subsequent attempt may need a freshly authenticated client.
            for client in ux.current.get().clients:
                client.client.close()
            ux.current.get().clients.clear()


def run():
    if not ux.is_interactive():
        raise ux.CLIError("getblock interactive requires a terminal. Use direct commands in scripts; see getblock --help.", 2)
    parent = ux.current.get() or ux.Runtime()
    state = copy.copy(parent)
    state.output = "table"
    state.fields = None
    state.clients = []
    state.secrets = list(parent.secrets)
    state.operation = "getblock interactive"
    token = ux.current.set(state)
    try:
        typer.echo("GetBlock interactive — profile: " + safe_text(state.profile), err=True)
        typer.echo("Choose a number and press Enter. Advanced services are unavailable pending authentication documentation.", err=True)
        while True:
            try:
                selected = menu("GetBlock", ["Account", "Protocols", "Tokens", "Exit"])
                section(selected)
            except Navigate as navigation:
                if navigation.destination == "Exit":
                    return
    finally:
        for client in state.clients:
            client.client.close()
        ux.current.reset(token)
