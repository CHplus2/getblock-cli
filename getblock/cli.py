import typer
import sys
import os
import httpx
import keyring
from importlib.metadata import version as package_version

from getblock import ux, config
from getblock.ux import emit, CLIError


from getblock.advanced_client import AdvancedGetBlockClient
from getblock.client import GetBlockClient, GetBlockAPIError
from getblock.auth import save_api_key, get_api_key, delete_api_key

app = typer.Typer(
    cls=ux.UXGroup,
    name = "getblock",
    help = "Manage account access, discover node configurations, and track operations. Start with auth login, then account show; see help workflows for examples. Advanced live access is unavailable; offline --dry-run previews work.",
)

tokens_app = typer.Typer(
    help="Manage GetBlock access tokens."
)

app.add_typer(tokens_app, name="tokens", rich_help_panel="Account and access")

auth_app = typer.Typer(
    help="Manage GetBlock authentication."
)

app.add_typer(auth_app, name="auth", rich_help_panel="Account and access")


def get_authenticated_client() -> GetBlockClient:
    state = ux.current.get() or ux.Runtime()
    if state.dry_run:
        client = GetBlockClient.__new__(GetBlockClient)
        client.preview = True
        return client
    for client in state.clients:
        if getattr(client, "_cli_surface", None) == "public":
            return client
    try:
        api_key = os.environ.get("GETBLOCK_API_KEY")
        if not api_key:
            api_key = get_api_key() if state.profile == "default" else get_api_key(state.profile)
    except keyring.errors.KeyringError:
        raise CLIError("Cannot access the system credential store. Configure keyring or use GETBLOCK_API_KEY for Public API automation.", 4)
    if not api_key:
        raise CLIError("Not authenticated. Run 'getblock auth login' first.", 4)
    state.secrets.append(api_key)
    client = GetBlockClient(api_key)
    client.client.timeout = httpx.Timeout(state.timeout)
    client._cli_surface = "public"
    state.clients.append(client)
    return client


def get_authenticated_advanced_client() -> AdvancedGetBlockClient:
    state = ux.current.get() or ux.Runtime()
    if state.dry_run:
        client = AdvancedGetBlockClient.__new__(AdvancedGetBlockClient)
        client.preview = True
        return client
    raise GetBlockAPIError(
        "Advanced API authentication is not configured: authoritative host, "
        "authentication header, and Public API key compatibility are required. "
        "Use --dry-run to inspect a request or getblock help advanced for details."
    )


def show_version(value: bool):
    if value:
        typer.echo("getblock " + package_version("getblock-cli"))
        raise typer.Exit()


@app.callback()
def callback(
    profile: str = typer.Option("default", envvar="GETBLOCK_PROFILE", help="Account profile; credentials stay in keyring."),
    timeout: float | None = typer.Option(None, help="Request timeout in seconds; overrides environment and profile."),
    verbose: bool = typer.Option(False, "--verbose", help="Redacted request diagnostics on stderr."),
    version: bool = typer.Option(False, "--version", callback=show_version, is_eager=True),
):
    """Manage account access, discover node configurations, and inspect operations.

    Start with auth login, then account show. Use help workflows for examples.
    Advanced services are unavailable pending authentication documentation;
    their --dry-run previews work offline.
    """
    state = ux.current.get()
    if state is None:
        state = ux.Runtime()
        ux.current.set(state)
    state.profile = config.profile_name(profile)
    settings, origins = config.resolve(state.profile, timeout=timeout)
    state.config_values = settings
    state.config_origins = origins
    state.output = "json" if getattr(state, "explicit_json", False) else settings["output"]
    state.timeout = settings["timeout"]
    state.verbose = verbose


@app.command()
@ux.command()
def me():
    """Show the authenticated GetBlock user."""
    
    client = get_authenticated_client()
    data = client.get_me()
    emit(data)


@tokens_app.command("list")
@ux.command(collection=True)
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
    emit(data)

@tokens_app.command("get")
@ux.command()
def get_token(token_id: str = typer.Argument(
    ...,
    help="ID of the GetBlock access token.",
)):
    """Get an access token by ID."""

    client = get_authenticated_client()
    data = client.get_token(token_id)
    
    emit(data)

@tokens_app.command("create")
@ux.command(input_fields={'protocol': 'protocol', 'network': 'network', 'api': 'api', 'mode': 'mode', 'region': 'region', 'addon': 'addon'}, interactive=True)
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
    
    emit(data)

@tokens_app.command("delete")
@ux.command(mutation='This cannot be undone.')
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


    client.delete_token(token_id)

    emit({"id": token_id, "deleted": True})

@tokens_app.command("rotate")
@ux.command(mutation='The old token stops working immediately.')
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
    

    data = client.rotate_token(token_id)

    emit(data)


@auth_app.command("login")
@ux.command()
def auth_login(
    with_key: bool = typer.Option(False, "--with-key", help="Read a Public API key from stdin, never from argv."),
):
    """Store a Public API key in keyring. Verify separately with auth status --check."""
    state = ux.current.get()
    if state.dry_run:
        raise CLIError("Login stores credentials; --dry-run is not supported.", 2)
    if with_key:
        api_key = sys.stdin.read().strip()
    else:
        if not ux.is_interactive():
            raise CLIError("Use --with-key to read a key from stdin in noninteractive use.", 2)
        api_key = ux.prompt("Public API key", hide_input=True)
    if not api_key or "\n" in api_key or "\r" in api_key:
        raise CLIError("Provide one nonempty API key.", 2)
    state.secrets.append(api_key)
    try:
        save_api_key(api_key, state.profile)
    except keyring.errors.KeyringError:
        raise CLIError("Cannot save to keyring. Configure a credential-store backend; no plaintext fallback is used.", 4)
    emit({"profile": state.profile, "stored": True, "verified": False})


@auth_app.command("status")
@ux.command()
def auth_status(
    check: bool = typer.Option(False, "--check", help="Verify Public credentials through GET /api/v1/me."),
    api: str = typer.Option("public", help="API surface: public or advanced."),
):
    """Distinguish stored credentials from verified access. Never display the key."""
    state = ux.current.get()
    if api not in ("public", "advanced"):
        raise CLIError("--api must be public or advanced.", 2)
    if api == "advanced":
        if check:
            get_authenticated_advanced_client()
        emit({"api": api, "available": False, "reason": "Authentication contract unconfirmed; use help advanced."})
        return
    if state.dry_run:
        if not check:
            raise CLIError("Use auth status --check --dry-run to preview verification.", 2)
        get_authenticated_client().get_me()
        return
    source = "environment" if os.environ.get("GETBLOCK_API_KEY") else "keyring"
    try:
        configured = bool(os.environ.get("GETBLOCK_API_KEY") or (get_api_key() if state.profile == "default" else get_api_key(state.profile)))
    except keyring.errors.KeyringError:
        raise CLIError("Cannot access keyring. Configure the credential store or GETBLOCK_API_KEY.", 4)
    if check:
        get_authenticated_client().get_me()
    emit({"api": api, "profile": state.profile, "configured": configured, "source": source if configured else None, "verified": bool(check)})


@auth_app.command("logout")
@ux.command()
def auth_logout():
    """Remove this profile's stored key. Environment credentials are unaffected."""
    state = ux.current.get()
    if state.dry_run:
        emit({"dry_run": True, "action": "remove stored credential", "profile": state.profile})
        return
    try:
        delete_api_key(state.profile)
    except keyring.errors.KeyringError:
        raise CLIError("Cannot remove credential from keyring. Check the credential store.", 4)
    emit({"profile": state.profile, "stored": False, "environment_active": bool(os.environ.get("GETBLOCK_API_KEY"))})


dedicated_app = typer.Typer(help="Browse GetBlock dedicated nodes.")
app.add_typer(dedicated_app, name="dedicated", rich_help_panel="Nodes")


dedicated_tokens_app = typer.Typer(help="Create tokens bound to a dedicated node.")
dedicated_app.add_typer(dedicated_tokens_app, name="tokens", rich_help_panel="Account and access")


@dedicated_app.command("list")
@ux.command(collection=True)
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
    emit(data)


@dedicated_app.command("get")
@ux.command()
def get_dedicated_node(
    node_id: str = typer.Argument(..., help="Node ID."),
):
    """Get a dedicated node by ID."""
    client = get_authenticated_client()
    data = client.get_dedicated_node(node_id)
    emit(data)


@dedicated_tokens_app.command("create")
@ux.command(input_fields={'api': 'api', 'addon': 'addon'}, interactive=True)
def create_dedicated_token(
    node_id: str = typer.Argument(..., help="Node ID."),
    api: str = typer.Option(..., "--api", help="API type supported by the node."),
    addon: str = typer.Option("", help="Addon; empty string means no addon."),
):
    """Create a node-bound token."""
    client = get_authenticated_client()
    data = client.create_dedicated_token(node_id, api=api, addon=addon)
    emit(data)


limitless_app = typer.Typer(help="Browse GetBlock limitless nodes.")
app.add_typer(limitless_app, name="limitless", rich_help_panel="Nodes")


limitless_tokens_app = typer.Typer(help="Create tokens bound to a limitless node.")
limitless_app.add_typer(limitless_tokens_app, name="tokens", rich_help_panel="Account and access")


@limitless_app.command("list")
@ux.command(collection=True)
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
    emit(data)


@limitless_app.command("get")
@ux.command()
def get_limitless_node(
    node_id: str = typer.Argument(..., help="Node ID."),
):
    """Get a limitless node by ID."""
    client = get_authenticated_client()
    data = client.get_limitless_node(node_id)
    emit(data)


@limitless_tokens_app.command("create")
@ux.command(input_fields={'api': 'api', 'addon': 'addon'}, interactive=True)
def create_limitless_token(
    node_id: str = typer.Argument(..., help="Node ID."),
    api: str = typer.Option(..., "--api", help="API type supported by the node."),
    addon: str = typer.Option("", help="Addon; empty string means no addon."),
):
    """Create a node-bound token."""
    client = get_authenticated_client()
    data = client.create_limitless_token(node_id, api=api, addon=addon)
    emit(data)


subscriptions_app = typer.Typer(help="Browse GetBlock subscriptions.")
app.add_typer(subscriptions_app, name="subscriptions", rich_help_panel="Account and access")


@app.command("subscription")
@ux.command()
def get_subscription():
    """Show the current plan and limits, including when no plan is active."""
    client = get_authenticated_client()
    data = client.get_subscription()
    emit(data)


@subscriptions_app.command("list")
@ux.command(collection=True)
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
    emit(data)


@subscriptions_app.command("get")
@ux.command()
def get_subscription_by_id(
    subscription_id: str = typer.Argument(..., help="Subscription ID."),
):
    """Get a subscription by ID."""
    client = get_authenticated_client()
    data = client.get_subscription_by_id(subscription_id)
    emit(data)


protocols_app = typer.Typer(help="Browse GetBlock protocols.")
app.add_typer(protocols_app, name="protocols", rich_help_panel="Catalog")


@protocols_app.command("list")
@ux.command(collection=True)
def get_protocols(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
):
    """List protocols."""
    client = get_authenticated_client()
    data = client.get_protocols(limit=limit, offset=offset, search=search)
    emit(data)


@protocols_app.command("get")
@ux.command()
def get_protocol(
    protocol_id: str = typer.Argument(..., help="Protocol ID."),
):
    """Get the full configuration for a protocol."""
    client = get_authenticated_client()
    data = client.get_protocol(protocol_id)
    emit(data)


addons_app = typer.Typer(help="Browse GetBlock addons.")
app.add_typer(addons_app, name="addons", rich_help_panel="Catalog")


@addons_app.command("list")
@ux.command(collection=True)
def get_addons(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
    protocol: str | None = typer.Option(None, help="Filter by protocol."),
):
    """List addons."""
    client = get_authenticated_client()
    data = client.get_addons(limit=limit, offset=offset, search=search, protocol=protocol)
    emit(data)


pricing_app = typer.Typer(help="Browse GetBlock pricing.")
app.add_typer(pricing_app, name="pricing", rich_help_panel="Catalog")


@pricing_app.command("list")
@ux.command(collection=True)
def get_pricing(
    limit: int = typer.Option(20, help="Maximum number of results to return."),
    offset: int = typer.Option(0, help="Number of matching results to skip."),
    search: str | None = typer.Option(None, help="Search results."),
):
    """List plan prices in whole units of the stated currency."""
    client = get_authenticated_client()
    data = client.get_pricing(limit=limit, offset=offset, search=search)
    emit(data)


@app.command("balance")
@ux.command()
def get_balance():
    """Show CU balances and credit balance in cents."""
    client = get_authenticated_client()
    data = client.get_balance()
    emit(data)



tron_energy_app = typer.Typer(help="GetBlock tron-energy services.")
app.add_typer(tron_energy_app, name="tron-energy", rich_help_panel="Advanced services (connection unavailable)")


@tron_energy_app.command("price-estimate")
@ux.command(advanced=True, input_fields={'resource_type': 'resourceType', 'volume': 'volume', 'duration': 'duration'}, estimate=True)
def estimate_tron_price(
    resource_type: str = typer.Option(..., help="Resource type: energy or bandwidth; validated by the server."),
    volume: int = typer.Option(..., help="Volume; documented minimum 1, validated by the server."),
    duration: str = typer.Option(..., help="Duration supported by the service; no local values or defaults are assumed."),
):
    """Estimate TRON price."""
    client = get_authenticated_advanced_client()
    data = client.estimate_tron_price(
        resource_type=resource_type,
        volume=volume,
        duration=duration,
    )
    emit(data)


@tron_energy_app.command("address-status")
@ux.command(advanced=True)
def get_tron_address_status(
    address: str = typer.Argument(..., help="Address."),
):
    """Get TRON address status."""
    client = get_authenticated_advanced_client()
    data = client.get_tron_address_status(
        address=address,
    )
    emit(data)


@tron_energy_app.command("address-activation-estimate")
@ux.command(advanced=True)
def estimate_tron_address_activation():
    """Estimate TRON address activation."""
    client = get_authenticated_advanced_client()
    data = client.estimate_tron_address_activation()
    emit(data)


tron_orders_app = typer.Typer(help="Inspect TRON resource orders.")
tron_energy_app.add_typer(tron_orders_app, name="orders")


@tron_orders_app.command("list")
@ux.command(collection=True, advanced=True)
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
    emit(data)


@tron_orders_app.command("get")
@ux.command(advanced=True)
def get_tron_order(
    order_id: str = typer.Argument(..., help="Order id."),
):
    """Get TRON order."""
    client = get_authenticated_advanced_client()
    data = client.get_tron_order(
        order_id=order_id,
    )
    emit(data)


@tron_energy_app.command("delegate-energy")
@ux.command(advanced=True, paid=True, input_fields={'target_address': 'target_address', 'volume': 'volume', 'duration': 'duration', 'quote_token': 'quote_token'}, quote=True)
def delegate_tron_energy(
    target_address: str = typer.Option(..., help="TRON target address: T followed by 33 ASCII letters/digits; validated by the server."),
    volume: int = typer.Option(..., help="Volume; documented minimum 1, validated by the server."),
    duration: str = typer.Option(..., help="Duration supported by the service; no local values or defaults are assumed."),
    quote_token: str = typer.Option(..., help="quote_token returned by tron-energy price-estimate; never displayed in previews."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Delegate TRON energy."""
    client = get_authenticated_advanced_client()
    data = client.delegate_tron_energy(
        target_address=target_address,
        volume=volume,
        duration=duration,
        quote_token=quote_token,
    )
    emit(data)


@tron_energy_app.command("delegate-bandwidth")
@ux.command(advanced=True, paid=True, input_fields={'target_address': 'target_address', 'volume': 'volume', 'duration': 'duration', 'quote_token': 'quote_token'}, quote=True)
def delegate_tron_bandwidth(
    target_address: str = typer.Option(..., help="TRON target address: T followed by 33 ASCII letters/digits; validated by the server."),
    volume: int = typer.Option(..., help="Volume; documented minimum 1, validated by the server."),
    duration: str = typer.Option(..., help="Duration supported by the service; no local values or defaults are assumed."),
    quote_token: str = typer.Option(..., help="quote_token returned by tron-energy price-estimate; never displayed in previews."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Delegate TRON bandwidth."""
    client = get_authenticated_advanced_client()
    data = client.delegate_tron_bandwidth(
        target_address=target_address,
        volume=volume,
        duration=duration,
        quote_token=quote_token,
    )
    emit(data)


@tron_energy_app.command("address-activate")
@ux.command(advanced=True, paid=True)
def activate_tron_address(
    target_address: str = typer.Argument(..., help="TRON target address: T followed by 33 ASCII letters/digits; validated by the server."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed without confirmation."),
):
    """Activate TRON address."""
    client = get_authenticated_advanced_client()
    data = client.activate_tron_address(
        target_address=target_address,
    )
    emit(data)


wallet_audit_app = typer.Typer(help="GetBlock wallet-audit services.")
app.add_typer(wallet_audit_app, name="wallet-audit", rich_help_panel="Advanced services (connection unavailable)")


@wallet_audit_app.command("audit")
@ux.command(advanced=True, paid=True, input_fields={'network': 'network', 'address': 'address'})
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
    emit(data)


@wallet_audit_app.command("check")
@ux.command(advanced=True, paid=True, input_fields={'network': 'network', 'address': 'address'})
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
    emit(data)


rug_pull_app = typer.Typer(help="GetBlock rug-pull services.")
app.add_typer(rug_pull_app, name="rug-pull", rich_help_panel="Advanced services (connection unavailable)")


@rug_pull_app.command("check")
@ux.command(advanced=True, paid=True, input_fields={'network': 'network', 'contract_address': 'contract_address'})
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
    emit(data)


aml_app = typer.Typer(help="GetBlock AML services.")
app.add_typer(aml_app, name="aml", rich_help_panel="Advanced services (connection unavailable)")


@aml_app.command("wallet-check")
@ux.command(advanced=True, paid=True, input_fields={'address': 'address', 'network': 'network'})
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
    emit(data)


@aml_app.command("tx-check")
@ux.command(advanced=True, paid=True, input_fields={'tx': 'tx', 'network': 'network', 'asset': 'asset'})
def check_aml_transaction(
    tx: str = typer.Option(..., help="Tx."),
    network: str = typer.Option(..., help="Network."),
    asset: str | None = typer.Option(None, help="Asset string; omitted from the request when not supplied."),
):
    """Check AML transaction. May consume prepaid units or Credits."""
    client = get_authenticated_advanced_client()
    data = client.check_aml_transaction(
        tx=tx,
        network=network,
        asset=asset,
    )
    emit(data)



account_app = typer.Typer(help="Account identity, current plan, and balances.")
app.add_typer(account_app, name="account", rich_help_panel="Account and access")
account_app.command("show")(me)
account_app.command("plan")(get_subscription)
account_app.command("balance")(get_balance)

config_app = typer.Typer(help="Manage non-secret settings for the selected profile.")
app.add_typer(config_app, name="config", rich_help_panel="CLI tools")


@config_app.command("list")
@ux.command()
def config_list(show_origin: bool = typer.Option(False, "--show-origin")):
    """Show effective settings and optionally where they came from."""
    state = ux.current.get()
    values = getattr(state, "config_values", config.DEFAULTS)
    origins = getattr(state, "config_origins", {})
    emit({"profile": state.profile, "path": str(config.config_path()), "settings": values, **({"origins": origins} if show_origin else {})})


@config_app.command("set")
@ux.command()
def config_set(key: str, value: str):
    """Set output=table|json|tsv or timeout=positive seconds. Never stores secrets."""
    state = ux.current.get()
    parsed = config.validate(key, value)
    if not state.dry_run:
        config.save(state.profile, key, parsed)
    emit({"profile": state.profile, "setting": key, "value": parsed, "saved": not state.dry_run})


@app.command("help", rich_help_panel="CLI tools")
def help_topic(topic: str = typer.Argument("workflows", help="workflows, shell, advanced, exit-codes, configuration", autocompletion=ux.complete_from(["workflows", "shell", "advanced", "exit-codes", "configuration"]))):
    """Examples, shell setup, configuration, Advanced availability and exit codes."""
    from getblock.help_topics import TOPICS
    if topic not in TOPICS:
        raise CLIError("Unknown help topic. Choose: " + ", ".join(TOPICS), 2)
    typer.echo(TOPICS[topic])


@tron_orders_app.command("watch")
@ux.command(advanced=True)
def watch_tron_order(
    order_id: str = typer.Argument(..., help="Order UUID to inspect; no delegation is performed."),
    interval: float = typer.Option(5, min=0.1, help="Seconds between GET requests."),
    timeout: float = typer.Option(120, min=0.1, help="Overall watch deadline in seconds."),
    status_field: str | None = typer.Option(None, help="Explicit dot path to the observed status, e.g. data.status, after verifying the response."),
    until_status: str | None = typer.Option(None, help="Stop on this exact value. No terminal-state meanings are assumed."),
):
    """Observe an order with bounded polling. Acceptance is not delivery."""
    import time
    import math
    if not math.isfinite(interval) or not math.isfinite(timeout):
        raise CLIError("Watch interval and timeout must be finite.", 2)
    if bool(status_field) != bool(until_status):
        raise CLIError("Provide both --status-field and --until-status, or neither.", 2)
    client = get_authenticated_advanced_client()
    start = time.monotonic()
    while True:
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise CLIError("Watch deadline reached; order completion has not been established.", 5)
        if not ux.current.get().dry_run:
            client.client.timeout = httpx.Timeout(min(ux.current.get().timeout, remaining))
        data = client.get_tron_order(order_id)
        value = data
        if status_field:
            for part in status_field.split("."):
                if not isinstance(value, dict) or part not in value:
                    raise CLIError("The selected --status-field is absent from the order response.", 2)
                value = value[part]
            if value == until_status:
                emit(data)
                return
        if ux.current.get().output != "json":
            typer.echo("Order " + ux.clean(order_id) + ": " + (ux.clean(value) if status_field else "observed; no completion condition specified"), err=True)
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise CLIError("Watch deadline reached; order completion has not been established.", 5)
        time.sleep(min(interval, remaining))


webhooks_app = typer.Typer(help="Manage Notify webhooks. Start with limits, then create --input FILE.")
webhook_secret_app = typer.Typer(help="Rotate webhook signing secrets.")
address_lists_app = typer.Typer(help="Manage named address lists shared by webhooks.")
address_entries_app = typer.Typer(help="List, add, replace or remove addresses in a named list.")
app.add_typer(webhooks_app, name="webhooks", rich_help_panel="Notify")
webhooks_app.add_typer(webhook_secret_app, name="secret")
app.add_typer(address_lists_app, name="address-lists", rich_help_panel="Notify")
address_lists_app.add_typer(address_entries_app, name="entries")


def _notify_body(path, allowed, required=()):
    """Check documented top-level keys; leave nested grammar and values intact."""
    body = ux.read_object(path)
    if set(body) - set(allowed):
        raise CLIError("Input contains unsupported request fields.", 2)
    missing = set(required) - set(body)
    if missing:
        raise CLIError("Missing required input fields: " + ", ".join(sorted(missing)), 2)
    return body


@webhooks_app.command("create")
@ux.command()
def create_webhook(request_file: str = typer.Option(..., "--input", help="Webhook JSON object from file, or - for stdin.")):
    """Create a webhook. Use --json to capture its one-time signing secret."""
    body = _notify_body(request_file,
        ("name", "chain", "network", "trigger_type", "filters", "confirm_depth", "phases", "target_url", "batching", "addresses", "list_refs"),
        ("chain", "trigger_type", "phases", "target_url"))
    emit(get_authenticated_client().create_webhook(body))


@webhooks_app.command("update")
@ux.command()
def update_webhook(
    webhook_id: str = typer.Argument(..., help="Webhook ID."),
    request_file: str = typer.Option(..., "--input", help="PATCH JSON object from file, or - for stdin; omitted keys stay unchanged."),
):
    """Update settings. confirm_depth:null resets depth; addresses:[] clears inline addresses."""
    body = _notify_body(request_file,
        ("name", "filters", "confirm_depth", "phases", "target_url", "batching", "addresses", "list_refs"))
    emit(get_authenticated_client().update_webhook(webhook_id, body))


@webhook_secret_app.command("rotate")
@ux.command(mutation="A second rotation during the 24-hour overlap retires the older secret immediately. --expire-previous also retires the current secret immediately.")
def rotate_webhook_secret(
    webhook_id: str = typer.Argument(..., help="Webhook ID."),
    expire_previous: bool = typer.Option(False, "--expire-previous", help="Immediately expire the previous secret; otherwise allow the documented 24-hour overlap."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm secret rotation."),
):
    """Rotate the signing secret. Capture the one-time secret with --json."""
    emit(get_authenticated_client().rotate_webhook_secret(webhook_id, True if expire_previous else None))


@webhooks_app.command("deliveries")
@ux.command(collection=True)
def get_webhook_deliveries(
    webhook_id: str = typer.Argument(..., help="Webhook ID."),
    limit: int = typer.Option(100, help="Page size; the server caps values above 999."),
    cursor: str | None = typer.Option(None, help="Opaque next_cursor returned by this endpoint."),
    from_time: str | None = typer.Option(None, "--from", help="RFC 3339 inclusive start time."),
    to_time: str | None = typer.Option(None, "--to", help="RFC 3339 exclusive end time."),
    status: list[str] | None = typer.Option(None, help="Repeatable or comma-separated: delivered, retrying, failed_terminal, replayed.", autocompletion=ux.complete_from(["delivered", "retrying", "failed_terminal", "replayed"])),
):
    """Inspect retries/failures and test events. Logs may be sampled; use stats for totals."""
    emit(get_authenticated_client().get_webhook_deliveries(webhook_id, limit, cursor, from_time, to_time, status))


@address_lists_app.command("create")
@ux.command()
def create_address_list(request_file: str = typer.Option(..., "--input", help="JSON object with name and optional addresses; file or - for stdin.")):
    """Create a named address list, optionally with initial addresses."""
    body = _notify_body(request_file, ("name", "addresses"), ("name",))
    emit(get_authenticated_client().create_address_list(body))


@address_lists_app.command("rename")
@ux.command(input_fields={"name": "name"})
def rename_address_list(
    list_id: str = typer.Argument(..., help="Address list ID."),
    name: str = typer.Option(..., help="New list name."),
):
    """Rename an address list without changing its entries."""
    emit(get_authenticated_client().rename_address_list(list_id, name))


@webhooks_app.command("list")
@ux.command(collection=True)
def get_webhooks(
    limit: int = typer.Option(50, help="Page size; the server caps values above 200."),
    cursor: str | None = typer.Option(None, help="Opaque next_cursor returned by this endpoint."),
):
    """List webhooks, newest first; signing secrets are never returned."""
    emit(get_authenticated_client().get_webhooks(limit=limit, cursor=cursor))


@webhooks_app.command("addresses")
@ux.command(collection=True)
def get_webhook_addresses(
    webhook_id: str = typer.Argument(..., help="Resource ID."),
    limit: int = typer.Option(50, help="Page size; the server caps values above 200."),
    cursor: str | None = typer.Option(None, help="Opaque next_cursor returned by this endpoint."),
):
    """List only the webhook's inline addresses, not addresses from shared list_refs."""
    emit(get_authenticated_client().get_webhook_addresses(webhook_id, limit=limit, cursor=cursor))


@address_lists_app.command("list")
@ux.command(collection=True)
def get_address_lists(
    limit: int = typer.Option(50, help="Page size; the server caps values above 200."),
    cursor: str | None = typer.Option(None, help="Opaque next_cursor returned by this endpoint."),
):
    """List named address lists, newest first."""
    emit(get_authenticated_client().get_address_lists(limit=limit, cursor=cursor))


@address_entries_app.command("list")
@ux.command(collection=True)
def get_address_list_entries(
    list_id: str = typer.Argument(..., help="Resource ID."),
    limit: int = typer.Option(50, help="Page size; the server caps values above 200."),
    cursor: str | None = typer.Option(None, help="Opaque next_cursor returned by this endpoint."),
):
    """List the addresses in a named list."""
    emit(get_authenticated_client().get_address_list_entries(list_id, limit=limit, cursor=cursor))


@webhooks_app.command("limits")
@ux.command()
def get_webhook_limits():
    """Show advisory plan caps and current address usage; create checks limits again."""
    emit(get_authenticated_client().get_webhook_limits())


@webhooks_app.command("get")
@ux.command()
def get_webhook(webhook_id: str = typer.Argument(..., help="Resource ID.")):
    """Get a webhook without its signing secret."""
    emit(get_authenticated_client().get_webhook(webhook_id))


@webhooks_app.command("pause")
@ux.command()
def pause_webhook(webhook_id: str = typer.Argument(..., help="Resource ID.")):
    """Stop deliveries until resumed. The webhook keeps its plan slot."""
    emit(get_authenticated_client().pause_webhook(webhook_id))


@webhooks_app.command("resume")
@ux.command()
def resume_webhook(webhook_id: str = typer.Argument(..., help="Resource ID.")):
    """Resume deliveries if the current plan and balance allow it."""
    emit(get_authenticated_client().resume_webhook(webhook_id))


@webhooks_app.command("test")
@ux.command()
def send_webhook_test(webhook_id: str = typer.Argument(..., help="Resource ID.")):
    """Queue one signed test event. 202 means queued, not delivered; inspect deliveries and stats."""
    emit(get_authenticated_client().send_webhook_test(webhook_id))


@webhooks_app.command("stats")
@ux.command()
def get_webhook_stats(webhook_id: str = typer.Argument(..., help="Resource ID.")):
    """Show delivery totals and available short-window rates. Totals can lag a few seconds."""
    emit(get_authenticated_client().get_webhook_stats(webhook_id))


@address_lists_app.command("get")
@ux.command()
def get_address_list(list_id: str = typer.Argument(..., help="Resource ID.")):
    """Get a named list's metadata; use entries list for its addresses."""
    emit(get_authenticated_client().get_address_list(list_id))


@webhooks_app.command("delete")
@ux.command(mutation="Deliveries stop; the webhook, statistics and delivery log cannot be recovered.")
def delete_webhook(
    webhook_id: str = typer.Argument(..., help="Resource ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion."),
):
    """Deliveries stop; the webhook, statistics and delivery log cannot be recovered."""
    get_authenticated_client().delete_webhook(webhook_id)
    emit({"id": webhook_id, "deleted": True})


@address_lists_app.command("delete")
@ux.command(mutation="This cannot be undone. A list referenced by a webhook cannot be deleted.")
def delete_address_list(
    list_id: str = typer.Argument(..., help="Resource ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion."),
):
    """This cannot be undone. A list referenced by a webhook cannot be deleted."""
    get_authenticated_client().delete_address_list(list_id)
    emit({"id": list_id, "deleted": True})


@address_entries_app.command("add")
@ux.command()
def add_address_list_entries(
    list_id: str = typer.Argument(..., help="Address list ID."),
    request_file: str = typer.Option(..., "--input", help="JSON object containing addresses; file or - for stdin."),
):
    """Add addresses using the documented entries operation."""
    body = _notify_body(request_file, ("addresses",), ("addresses",))
    if not isinstance(body["addresses"], list) or any(not isinstance(item, str) for item in body["addresses"]):
        raise CLIError("addresses must be an array of strings.", 2)
    client = get_authenticated_client()
    emit(client.add_address_list_entries(list_id, body["addresses"]))


@address_entries_app.command("replace")
@ux.command()
def replace_address_list_entries(
    list_id: str = typer.Argument(..., help="Address list ID."),
    request_file: str = typer.Option(..., "--input", help="JSON object containing addresses; file or - for stdin."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the address change."),
):
    """Replace addresses using the documented entries operation."""
    body = _notify_body(request_file, ("addresses",), ("addresses",))
    if not isinstance(body["addresses"], list) or any(not isinstance(item, str) for item in body["addresses"]):
        raise CLIError("addresses must be an array of strings.", 2)
    client = get_authenticated_client()
    if not ux.current.get().dry_run:
        ux.confirm("Address list " + ux.clean(list_id) + ": Replace every entry in this list? An empty array clears the list; referencing webhooks are affected.", yes)
    emit(client.replace_address_list_entries(list_id, body["addresses"]))


@address_entries_app.command("remove")
@ux.command()
def remove_address_list_entries(
    list_id: str = typer.Argument(..., help="Address list ID."),
    request_file: str = typer.Option(..., "--input", help="JSON object containing addresses; file or - for stdin."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the address change."),
):
    """Remove addresses using the documented entries operation."""
    body = _notify_body(request_file, ("addresses",), ("addresses",))
    if not isinstance(body["addresses"], list) or any(not isinstance(item, str) for item in body["addresses"]):
        raise CLIError("addresses must be an array of strings.", 2)
    client = get_authenticated_client()
    if not ux.current.get().dry_run:
        ux.confirm("Address list " + ux.clean(list_id) + ": Remove the supplied entries from this list? Referencing webhooks are affected.", yes)
    emit(client.remove_address_list_entries(list_id, body["addresses"]))


@app.command("interactive", rich_help_panel="CLI tools")
def interactive():
    """Navigate account, protocol and token discovery menus (terminal only)."""
    from getblock.interactive import run
    run()


from getblock.help_topics import configure_help

configure_help(app)


def main():
    try:
        app(prog_name="getblock")
    except GetBlockAPIError as error:
        typer.echo(f"Error: {error}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()