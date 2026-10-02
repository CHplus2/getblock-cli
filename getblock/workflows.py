"""Developer workflows built from the existing documented client methods."""
import json
import os
import sys
from pathlib import Path
import typer

from getblock.ux import CLIError, current, read_object, is_interactive, prompt, confirm
from getblock.output import rows_of, safe_text


def choose(label, values, selected=None):
    values = list(dict.fromkeys(values))
    if not values:
        raise CLIError(f"The API returned no available {label} values.")
    if selected is not None:
        if selected not in values:
            raise CLIError(f"Selected {label} is not available in the returned configuration.", 2)
        return selected
    typer.echo(label.capitalize() + ":", err=True)
    for i, value in enumerate(values, 1):
        typer.echo(f"  {i}. {safe_text(value) if value else '(no addon)'}", err=True)
    while True:
        number = prompt("Choose a number", type=int)
        if 1 <= number <= len(values):
            return values[number - 1]
        typer.echo(f"Choose a number from 1 to {len(values)}.", err=True)


def by_id(items, selected):
    return next(item for item in items if item["id"] == selected)


def guide_token(method, values):
    if not is_interactive():
        raise CLIError("--interactive requires a terminal. Supply explicit flags in scripts.", 2)
    from getblock import cli
    client = cli.get_authenticated_client()
    if method != "create_token":
        node = (client.get_dedicated_node if method == "create_dedicated_token" else client.get_limitless_node)(values["node_id"])
        values["api"] = choose("API", node.get("apis", []), values.get("api"))
        values["addon"] = choose("addon", [""] + node.get("addons", []), values.get("addon") or None)
    else:
        state = current.get()
        previous = state.paginate
        try:
            state.paginate = True
            catalog = rows_of(client.get_protocols())
        finally:
            state.paginate = previous
        values["protocol"] = choose("protocol", [item["id"] for item in catalog], values.get("protocol"))
        protocol = client.get_protocol(values["protocol"])
        networks = protocol.get("networks", [])
        values["network"] = choose("network", [item["id"] for item in networks], values.get("network"))
        network = by_id(networks, values["network"])
        modes = network.get("modes", [])
        values["mode"] = choose("mode", [item["id"] for item in modes], values.get("mode"))
        mode = by_id(modes, values["mode"])
        addons = mode.get("addons", [])
        values["addon"] = choose("addon", [""] + [item["id"] for item in addons], values.get("addon") or None)
        apis = mode.get("apis", []) if not values["addon"] else by_id(addons, values["addon"]).get("apis", [])
        values["api"] = choose("API", [item["id"] for item in apis], values.get("api"))
        values["region"] = choose("region", by_id(apis, values["api"]).get("regions", []), values.get("region"))
    typer.echo("Selected configuration (profile=" + current.get().profile + "):", err=True)
    for key, value in values.items():
        typer.echo(f"  {key}: {safe_text(value)}", err=True)
    confirm("Create this token?", False)
    return values


def save_quote(path, inputs, response):
    if not isinstance(response, dict) or not isinstance(response.get("data"), dict) or not isinstance(response["data"].get("quote_token"), str):
        raise CLIError("Estimate has no usable quote_token; no quote file written.")
    # Exclusive creation prevents silently replacing a different quote.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"inputs": inputs, "estimate": response}, stream, ensure_ascii=False)
        stream.write("\n")
    typer.echo("Quote saved. Treat this file as sensitive; server validity is not guaranteed.", err=True)


def load_quote(path, method, values):
    data = read_object(path)
    expected = {"resourceType": "energy" if method == "delegate_tron_energy" else "bandwidth", "volume": values["volume"], "duration": values["duration"]}
    inputs = data.get("inputs")
    if not isinstance(inputs, dict) or type(inputs.get("volume")) is not int or inputs != expected:
        raise CLIError("Quote inputs do not match resource, volume and duration. Obtain a matching estimate.", 2)
    estimate = data.get("estimate")
    body = estimate.get("data") if isinstance(estimate, dict) else None
    token = body.get("quote_token") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise CLIError("Quote file has no usable quote_token.", 2)
    return token
