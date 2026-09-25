import typer
import sys

from getblock.client import GetBlockClient, GetBlockAPIError
from getblock.auth import save_api_key, get_api_key, delete_api_key

app = typer.Typer(
    name = "getblock",
    help = "A command-line interface for interacting with the GetBlock API.",
)

tokens_app = typer.Typer(
    help="Manage GetBlock access tokens."
)

app.add_typer(tokens_app, name="tokens")

auth_app = typer.Typer(
    help="Manage GetBlock authentication."
)

app.add_typer(auth_app, name="auth")


def get_authenticated_client() -> GetBlockClient:
    api_key = get_api_key()

    if not api_key:
        typer.echo("Not authenticated. Run 'getblock auth login' first.")
        raise typer.Exit(code=1)

    return GetBlockClient(api_key)


@app.callback()
def callback():
    """A command-line interface for interacting with the GetBlock API."""
    pass


@app.command()
def me():
    """Show the authenticated GetBlock user."""
    
    client = get_authenticated_client()
    data = client.get_me()
    print(data)


@tokens_app.command("list")
def list_tokens(
    limit: int = typer.Option(20, help="Maximum number of tokens to return."),
    offset: int = typer.Option(0, help="Number of matching tokens to skip."),
    name: str | None = typer.Option(None, help="Filter by token name."),
    protocol: str | None = typer.Option(None, help="Filter by protocol."),
    network: str | None = typer.Option(None, help="Filter by network."),
    region: str | None = typer.Option(None, help="Filter by region."),
    namespace: str | None = typer.Option(None, help="Filter by access type."),
):
    """List the caller's GetBlock access tokens."""

    client = get_authenticated_client()
    data = client.get_tokens(
        limit=limit,
        offset=offset,
        name=name,
        protocol=protocol,
        network=network,
        region=region,
        namespace=namespace
    )
    print(data)

@tokens_app.command("get")
def get_token(token_id: str = typer.Argument(
    ...,
    help="ID of the GetBlock access token.",
)):
    """Get an access token by ID."""

    client = get_authenticated_client()
    data = client.get_token(token_id)
    
    print(data)

@tokens_app.command("create")
def create_token(
    protocol: str = typer.Option(..., help="Blockchain protocol."),
    network: str = typer.Option(..., help="Blockchain network."),
    api: str = typer.Option(..., "--api", help="API type."),
    mode: str = typer.Option(..., help="Node mode."),
    region: str = typer.Option(..., help="Region."),
    addon: str = typer.Option("", help="Addon configuration."),
):
    """Create a shared GetBlock access token."""

    client = get_authenticated_client()
    data = client.create_token(
        protocol=protocol,
        network=network,
        api=api,
        mode=mode,
        region=region,
        addon=addon
    )
    
    print(data)

@tokens_app.command("delete")
def delete_token(
    token_id: str = typer.Argument(
        ...,
        help="ID of the GetBlock access token to delete.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete without asking for confirmation.",
    ),
):
    """Delete an access token."""

    client = get_authenticated_client()

    if not yes:
        confirmed = typer.confirm(
            f"Delete token {token_id}? This cannot be undone."
        )

        if not confirmed:
            typer.echo("Deletion cancelled.")
            raise typer.Exit()

    client.delete_token(token_id)

    typer.echo(f"Token {token_id} deleted.")

@tokens_app.command("rotate")
def rotate_token(
    token_id: str = typer.Argument(
        ...,
        help="ID of the GetBlock access token to rotate.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Rotate without asking for confirmation.",
    ),
):
    """Rotate an access token."""

    client = get_authenticated_client()
    
    if not yes:
        confirmed = typer.confirm(
            f"Rotate token {token_id}? The old token will stop working immediately."
        )

        if not confirmed:
            typer.echo("Rotation cancelled.")
            raise typer.Exit()

    data = client.rotate_token(token_id)

    print(data)


@auth_app.command("login")
def auth_login():
    """Save a GetBlock Public API key."""
    
    api_key = typer.prompt(
        "API key",
        hide_input=True,
    )
    save_api_key(api_key)
    typer.echo("API key saved.")

@auth_app.command("status")
def auth_status():
    """Show authentication status """

    api_key = get_api_key()
    if api_key:
        typer.echo("Authenticated credentials are configured.")
    else:
        typer.echo("No GetBlock credentials are configured.")

@auth_app.command("logout")
def auth_logout():
    """Remove stored GetBlock credentials."""

    delete_api_key()
    typer.echo("GetBlock credentials removed.")

def main():
    try:
        app()
    except GetBlockAPIError as error:
        typer.echo(f"Error: {error}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()