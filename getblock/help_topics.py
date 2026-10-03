"""Offline help topics. No API calls, credential access, or network completion."""
import inspect
TOPICS = {
    "workflows": """GET STARTED
  getblock auth login
  getblock auth status --check
  getblock account show
  getblock account plan
  getblock account balance

DISCOVER AND CREATE ACCESS
  getblock protocols list --search Ethereum
  getblock protocols get eth
  getblock tokens create --interactive
  getblock dedicated tokens create NODE_ID --interactive
  getblock tokens list --paginate --json

ESTIMATE, DELEGATE, TRACK (Advanced connection currently unavailable)
  getblock tron-energy price-estimate --resource-type energy --volume VOLUME --duration DURATION --save-quote quote.json
  getblock tron-energy delegate-energy --target-address ADDRESS --volume VOLUME --duration DURATION --quote-file quote.json
  getblock tron-energy orders get ORDER_ID
  getblock tron-energy orders watch ORDER_ID --interval 5 --timeout 120
Use documented duration values. Watch does not guess terminal states. An optional
--status-field and --until-status define your explicit stop condition.

AUTOMATION
  getblock tokens list --json | jq -r '.tokens[].id'
  getblock tokens list --output tsv --fields id,protocol
  getblock aml wallet-check --input request.json --yes --dry-run --json
JSON retains complete API responses and may contain endpoint credentials.
All paid commands require --yes without a terminal; no automatic POST retries.
""",
    "shell": """COMPLETION (offline, no API calls)
  getblock --install-completion
  getblock --show-completion
Typer supports Bash, Zsh, Fish, PowerShell and pwsh. Use --help on these options
to choose a shell when automatic detection is unavailable. Restart the shell
after installation. Completion never makes billable requests.

POWERSHELL
  $data = getblock tokens list --json | ConvertFrom-Json
  $data.tokens | Select-Object id, protocol
  Get-Content -Raw request.json | getblock aml wallet-check --input - --yes --dry-run --json

BASH / ZSH
  getblock tokens list --json | jq -r '.tokens[].id'
  getblock aml wallet-check --input request.json --yes --dry-run --json

Use --json explicitly in scripts. Data goes to stdout; diagnostics go to stderr.
Human output is plain text, with no ANSI colors or pager; NO_COLOR is respected.
Do not place API keys in command-line arguments or shell history. Configure the
CI secret GETBLOCK_API_KEY for Public API calls. --with-key reads from stdin.
""",
    "advanced": """ADVANCED SERVICES: CONNECTION UNAVAILABLE
The authoritative Advanced host, authentication header, and compatibility with
stored Public API keys have not been established. No credential is sent to an
Advanced service. Do not assume GETBLOCK_API_KEY authenticates this surface.

Available offline:
  getblock auth status --api advanced
  getblock tron-energy delegate-energy --target-address ADDRESS --volume 1 --duration DURATION --quote-token QUOTE --dry-run --json
  getblock wallet-audit audit --network ETH --address ADDRESS --dry-run

Previews omit credentials and redact quote tokens. They do not verify price,
server acceptance, quote expiry, or balance. Paths use /v1/, never /api/v1/.
Watch can poll once authentication is established, but no terminal-state
semantics are assumed for charged or delivered_uncharged.
""",
    "exit-codes": """EXIT CODES
  0  Requested operation completed, or offline preview rendered.
  1  API, network, configuration availability, or other operational failure.
  2  Invalid command arguments, input data, or setting.
  3  User cancelled, consent missing in noninteractive use, or interrupted.
  4  Missing/invalid authentication or credential-store failure.
  5  Watch deadline reached before its explicit stop condition.

--json errors are one JSON object on stderr; stdout remains empty.
Paginated JSON is an array of whole page responses. A failed/bounded incomplete
pagination emits no partial export. API success 202 means accepted, not delivered.
""",
    "configuration": """CONFIGURATION
  getblock config list --show-origin
  getblock config set output json
  getblock --profile production config set timeout 30
  getblock --profile production auth login

Settings: flags > GETBLOCK_OUTPUT / GETBLOCK_TIMEOUT > selected profile > defaults.
Profile: --profile > GETBLOCK_PROFILE > default. Credentials: GETBLOCK_API_KEY
(Public only) > selected profile's keyring entry. The default profile preserves
the existing keyring entry. Profiles represent accounts, not server environments.
GETBLOCK_CONFIG_DIR chooses a user configuration directory. Repository files
are not loaded. Hosts, headers, credentials and persistent --yes are not settings.
""",
}


EXAMPLES = {
    "interactive": "",
    'create_webhook': '--input webhook.json --dry-run --json',
    'update_webhook': 'WEBHOOK_ID --input patch.json --dry-run --json',
    'rotate_webhook_secret': 'WEBHOOK_ID --dry-run --json',
    'get_webhook_deliveries': 'WEBHOOK_ID --status retrying --json',
    'get_webhook_addresses': 'WEBHOOK_ID --json',
    'get_webhook': 'WEBHOOK_ID --json',
    'pause_webhook': 'WEBHOOK_ID --dry-run',
    'resume_webhook': 'WEBHOOK_ID --dry-run',
    'send_webhook_test': 'WEBHOOK_ID --dry-run',
    'get_webhook_stats': 'WEBHOOK_ID --json',
    'delete_webhook': 'WEBHOOK_ID --dry-run',
    'create_address_list': '--input list.json --dry-run --json',
    'rename_address_list': 'LIST_ID --name "Treasury wallets" --dry-run',
    'get_address_list': 'LIST_ID --json',
    'delete_address_list': 'LIST_ID --dry-run',
    'get_address_list_entries': 'LIST_ID --json',
    'add_address_list_entries': 'LIST_ID --input addresses.json --dry-run',
    'replace_address_list_entries': 'LIST_ID --input addresses.json --dry-run',
    'remove_address_list_entries': 'LIST_ID --input addresses.json --dry-run',
    "me": "--json",
    "get_balance": "--json",
    "get_subscription": "--json",
    "get_token": "TOKEN_ID --json",
    "create_token": "--interactive",
    "delete_token": "TOKEN_ID --dry-run",
    "rotate_token": "TOKEN_ID --dry-run",
    "get_dedicated_node": "NODE_ID --json",
    "get_limitless_node": "NODE_ID --json",
    "create_dedicated_token": "NODE_ID --interactive",
    "create_limitless_token": "NODE_ID --interactive",
    "get_protocol": "eth --json",
    "get_subscription_by_id": "SUBSCRIPTION_ID --json",
    "estimate_tron_price": "--resource-type energy --volume 1 --duration DURATION --dry-run --json",
    "get_tron_address_status": "ADDRESS --dry-run",
    "estimate_tron_address_activation": "--dry-run",
    "get_tron_order": "ORDER_ID --dry-run",
    "delegate_tron_energy": "--target-address ADDRESS --volume 1 --duration DURATION --quote-token QUOTE --dry-run",
    "delegate_tron_bandwidth": "--target-address ADDRESS --volume 1 --duration DURATION --quote-token QUOTE --dry-run",
    "activate_tron_address": "ADDRESS --dry-run",
    "audit_wallet": "--network ETH --address ADDRESS --dry-run",
    "check_wallet": "--network TRON --address ADDRESS --dry-run",
    "check_rug_pull": "--network ETH --contract-address ADDRESS --dry-run",
    "check_aml_wallet": "--address ADDRESS --network eth --dry-run",
    "check_aml_transaction": "--tx TRANSACTION --network eth --dry-run",
    "watch_tron_order": "ORDER_ID --interval 5 --timeout 120 --dry-run",
    "auth_login": "--with-key",
    "auth_status": "--check",
    "auth_logout": "--dry-run",
    "config_set": "output json",
    "config_list": "--show-origin --json",
    "help_topic": "workflows",
}


def configure_help(group, path="getblock"):
    for info in group.registered_commands:
        function = info.callback
        name = info.name or function.__name__.replace("_", "-")
        example = EXAMPLES.get(function.__name__, "--json")
        details = "Example: " + path + " " + name + " " + example
        if path.startswith("getblock tron-energy") or path.startswith("getblock wallet-audit") or path.startswith("getblock rug-pull") or path.startswith("getblock aml"):
            details += "\n\nAdvanced connection unavailable. --dry-run is offline; see getblock help advanced."
        elif path not in ("getblock config", "getblock auth") and name not in ("help",):
            details += "\n\nAuthentication: getblock auth login. Raw --json responses retain all fields; token responses may contain credentials."
        if "tokens" in path:
            details += "\n\nDiscover supported values: getblock protocols get PROTOCOL_ID. Node token creation uses the selected node's configuration."
        if "delegate" in name:
            details += "\n\nFirst obtain a price-estimate; pass its quote_token or --quote-file. HTTP 202 is accepted, not delivered. Check orders get ORDER_ID next."
        if "paginate" in inspect.signature(function).parameters:
            position = "--cursor continues from an opaque next_cursor" if "cursor" in inspect.signature(function).parameters else "--offset skips results"
            details += "\n\n--limit is page size; " + position + ". --paginate fetches pages and JSON becomes an array of complete page responses."
        details += "\n\nMore examples: getblock help workflows. Scripting: getblock help exit-codes."
        info.epilog = details
        if path == "getblock" and name in ("me", "subscription", "balance"):
            info.rich_help_panel = "Account shortcuts (also available under account)"
    for info in group.registered_groups:
        configure_help(info.typer_instance, path + " " + info.name)
