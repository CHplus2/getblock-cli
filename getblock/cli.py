import typer
import sys

from getblock.advanced_client import AdvancedGetBlockClient
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


def get_authenticated_advanced_client() -> AdvancedGetBlockClient:
    raise GetBlockAPIError(
        "Advanced API authentication is not configured: authoritative host, "
        "authentication header, and Public API key compatibility are required."
    )


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


dedicated_app = typer.Typer(help="Browse GetBlock dedicated nodes.")
app.add_typer(dedicated_app, name="dedicated")


dedicated_tokens_app = typer.Typer(help="Create tokens bound to a dedicated node.")
dedicated_app.add_typer(dedicated_tokens_app, name="tokens")


@dedicated_app.command("list")
def get_dedicated_nodes(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    protocol: str | None = typer.Option(None, help="Filter by protocol."),
    network: str | None = typer.Option(None, help="Filter by network."),
    region: str | None = typer.Option(None, help="Filter by region."),
    status: str | None = typer.Option(None, help="Filter by status."),
):
    """List the caller's dedicated nodes."""
    client = get_authenticated_client()
    data = client.get_dedicated_nodes(
        limit=limit,
        offset=offset,
        protocol=protocol,
        network=network,
        region=region,
        status=status,
    )
    print(data)


@dedicated_app.command("get")
def get_dedicated_node(
    node_id: str = typer.Argument(..., help="Node ID."),
):
    """Get a dedicated node by ID."""
    client = get_authenticated_client()
    data = client.get_dedicated_node(node_id)
    print(data)


@dedicated_tokens_app.command("create")
def create_dedicated_token(
    node_id: str = typer.Argument(..., help="Node ID."),
    api: str = typer.Option(..., "--api", help="API type supported by the node."),
    addon: str = typer.Option("", help="Addon; empty string means no addon."),
):
    """Create a node-bound token."""
    client = get_authenticated_client()
    data = client.create_dedicated_token(node_id, api=api, addon=addon)
    print(data)


limitless_app = typer.Typer(help="Browse GetBlock limitless nodes.")
app.add_typer(limitless_app, name="limitless")


limitless_tokens_app = typer.Typer(help="Create tokens bound to a limitless node.")
limitless_app.add_typer(limitless_tokens_app, name="tokens")


@limitless_app.command("list")
def get_limitless_nodes(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    protocol: str | None = typer.Option(None, help="Filter by protocol."),
    network: str | None = typer.Option(None, help="Filter by network."),
    region: str | None = typer.Option(None, help="Filter by region."),
    status: str | None = typer.Option(None, help="Filter by status."),
):
    """List the caller's limitless nodes."""
    client = get_authenticated_client()
    data = client.get_limitless_nodes(
        limit=limit,
        offset=offset,
        protocol=protocol,
        network=network,
        region=region,
        status=status,
    )
    print(data)


@limitless_app.command("get")
def get_limitless_node(
    node_id: str = typer.Argument(..., help="Node ID."),
):
    """Get a limitless node by ID."""
    client = get_authenticated_client()
    data = client.get_limitless_node(node_id)
    print(data)


@limitless_tokens_app.command("create")
def create_limitless_token(
    node_id: str = typer.Argument(..., help="Node ID."),
    api: str = typer.Option(..., "--api", help="API type supported by the node."),
    addon: str = typer.Option("", help="Addon; empty string means no addon."),
):
    """Create a node-bound token."""
    client = get_authenticated_client()
    data = client.create_limitless_token(node_id, api=api, addon=addon)
    print(data)


subscriptions_app = typer.Typer(help="Browse GetBlock subscriptions.")
app.add_typer(subscriptions_app, name="subscriptions")


@app.command("subscription")
def get_subscription():
    """Show the current plan and limits, including when no plan is active."""
    client = get_authenticated_client()
    data = client.get_subscription()
    print(data)


@subscriptions_app.command("list")
def get_subscriptions(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    product_type: str | None = typer.Option(
        None, help="Filter by product type: plan, enterprise_plan, request_package."
    ),
    status: str | None = typer.Option(None, help="Filter by status."),
):
    """List subscriptions."""
    client = get_authenticated_client()
    data = client.get_subscriptions(limit=limit, offset=offset, product_type=product_type, status=status)
    print(data)


@subscriptions_app.command("get")
def get_subscription_by_id(
    subscription_id: str = typer.Argument(..., help="Subscription ID."),
):
    """Get a subscription by ID."""
    client = get_authenticated_client()
    data = client.get_subscription_by_id(subscription_id)
    print(data)


protocols_app = typer.Typer(help="Browse GetBlock protocols.")
app.add_typer(protocols_app, name="protocols")


@protocols_app.command("list")
def get_protocols(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
):
    """List protocols."""
    client = get_authenticated_client()
    data = client.get_protocols(limit=limit, offset=offset, search=search)
    print(data)


@protocols_app.command("get")
def get_protocol(
    protocol_id: str = typer.Argument(..., help="Protocol ID."),
):
    """Get the full configuration for a protocol."""
    client = get_authenticated_client()
    data = client.get_protocol(protocol_id)
    print(data)


addons_app = typer.Typer(help="Browse GetBlock addons.")
app.add_typer(addons_app, name="addons")


@addons_app.command("list")
def get_addons(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
    protocol: str | None = typer.Option(None, help="Filter by protocol."),
):
    """List addons."""
    client = get_authenticated_client()
    data = client.get_addons(limit=limit, offset=offset, search=search, protocol=protocol)
    print(data)


pricing_app = typer.Typer(help="Browse GetBlock pricing.")
app.add_typer(pricing_app, name="pricing")


@pricing_app.command("list")
def get_pricing(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
):
    """List plan prices in whole units of the stated currency."""
    client = get_authenticated_client()
    data = client.get_pricing(limit=limit, offset=offset, search=search)
    print(data)


@app.command("balance")
def get_balance():
    """Show CU balances and credit balance in cents."""
    client = get_authenticated_client()
    data = client.get_balance()
    print(data)



tron_energy_app = typer.Typer(help="GetBlock tron-energy services.")
app.add_typer(tron_energy_app, name="tron-energy")


@tron_energy_app.command("price-estimate")
def estimate_tron_price(
    resource_type: str = typer.Option(..., help="Resource type."),
    volume: int = typer.Option(..., help="Volume."),
    duration: str = typer.Option(..., help="Duration."),
):
    """Estimate TRON price."""
    client = get_authenticated_advanced_client()
    data = client.estimate_tron_price(
        resource_type=resource_type,
        volume=volume,
        duration=duration,
    )
    print(data)


@tron_energy_app.command("address-status")
def get_tron_address_status(
    address: str = typer.Argument(..., help="Address."),
):
    """Get TRON address status."""
    client = get_authenticated_advanced_client()
    data = client.get_tron_address_status(
        address=address,
    )
    print(data)


@tron_energy_app.command("address-activation-estimate")
def estimate_tron_address_activation():
    """Estimate TRON address activation."""
    client = get_authenticated_advanced_client()
    data = client.estimate_tron_address_activation()
    print(data)


tron_orders_app = typer.Typer(help="Inspect TRON resource orders.")
tron_energy_app.add_typer(tron_orders_app, name="orders")


@tron_orders_app.command("list")
def get_tron_orders(
    limit: int = typer.Option(20, help="Maximum orders to return (API maximum 100)."),
    offset: int = typer.Option(0, help="Number of matching orders to skip."),
    status: str | None = typer.Option(None, help="Filter: pending, processing, charged, failed, delivered_uncharged."),
    resource_type: str | None = typer.Option(None, help="Filter: energy, bandwidth."),
):
    """Get TRON orders."""
    client = get_authenticated_advanced_client()
    data = client.get_tron_orders(
        limit=limit,
        offset=offset,
        status=status,
        resource_type=resource_type,
    )
    print(data)


@tron_orders_app.command("get")
def get_tron_order(
    order_id: str = typer.Argument(..., help="Order id."),
):
    """Get TRON order."""
    client = get_authenticated_advanced_client()
    data = client.get_tron_order(
        order_id=order_id,
    )
    print(data)


@tron_energy_app.command("delegate-energy")
def delegate_tron_energy(
    target_address: str = typer.Option(..., help="Target address."),
    volume: int = typer.Option(..., help="Volume."),
    duration: str = typer.Option(..., help="Duration."),
    quote_token: str = typer.Option(..., help="Quote token."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Delegate TRON energy."""
    if not yes and not typer.confirm(
        f"Delegate energy to {target_address}? This may consume prepaid balance.",
        default=False,
    ):
        typer.echo("Operation cancelled.")
        raise typer.Exit()
    client = get_authenticated_advanced_client()
    data = client.delegate_tron_energy(
        target_address=target_address,
        volume=volume,
        duration=duration,
        quote_token=quote_token,
    )
    print(data)


@tron_energy_app.command("delegate-bandwidth")
def delegate_tron_bandwidth(
    target_address: str = typer.Option(..., help="Target address."),
    volume: int = typer.Option(..., help="Volume."),
    duration: str = typer.Option(..., help="Duration."),
    quote_token: str = typer.Option(..., help="Quote token."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Delegate TRON bandwidth."""
    if not yes and not typer.confirm(
        f"Delegate bandwidth to {target_address}? This may consume prepaid balance.",
        default=False,
    ):
        typer.echo("Operation cancelled.")
        raise typer.Exit()
    client = get_authenticated_advanced_client()
    data = client.delegate_tron_bandwidth(
        target_address=target_address,
        volume=volume,
        duration=duration,
        quote_token=quote_token,
    )
    print(data)


@tron_energy_app.command("address-activate")
def activate_tron_address(
    target_address: str = typer.Argument(..., help="Target address."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Activate TRON address."""
    if not yes and not typer.confirm(
        f"Activate address {target_address}? This may consume prepaid balance.",
        default=False,
    ):
        typer.echo("Operation cancelled.")
        raise typer.Exit()
    client = get_authenticated_advanced_client()
    data = client.activate_tron_address(
        target_address=target_address,
    )
    print(data)


wallet_audit_app = typer.Typer(help="GetBlock wallet-audit services.")
app.add_typer(wallet_audit_app, name="wallet-audit")


@wallet_audit_app.command("audit")
def audit_wallet(
    network: str = typer.Option(..., help="Network."),
    address: str = typer.Option(..., help="Address."),
):
    """Audit wallet. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.audit_wallet(
        network=network,
        address=address,
    )
    print(data)


@wallet_audit_app.command("check")
def check_wallet(
    network: str = typer.Option(..., help="Network."),
    address: str = typer.Option(..., help="Address."),
):
    """Check wallet. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.check_wallet(
        network=network,
        address=address,
    )
    print(data)


rug_pull_app = typer.Typer(help="GetBlock rug-pull services.")
app.add_typer(rug_pull_app, name="rug-pull")


@rug_pull_app.command("check")
def check_rug_pull(
    network: str = typer.Option(..., help="Network."),
    contract_address: str = typer.Option(..., help="Contract address."),
):
    """Check rug pull. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.check_rug_pull(
        network=network,
        contract_address=contract_address,
    )
    print(data)


aml_app = typer.Typer(help="GetBlock AML services.")
app.add_typer(aml_app, name="aml")


@aml_app.command("wallet-check")
def check_aml_wallet(
    address: str = typer.Option(..., help="Address."),
    network: str = typer.Option(..., help="Network."),
):
    """Check AML wallet. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.check_aml_wallet(
        address=address,
        network=network,
    )
    print(data)


@aml_app.command("tx-check")
def check_aml_transaction(
    tx: str = typer.Option(..., help="Tx."),
    network: str = typer.Option(..., help="Network."),
):
    """Check AML transaction. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.check_aml_transaction(
        tx=tx,
        network=network,
    )
    print(data)


def main():
    try:
        app()
    except GetBlockAPIError as error:
        typer.echo(f"Error: {error}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()