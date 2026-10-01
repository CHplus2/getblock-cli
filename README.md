# GetBlock CLI

Python CLI using Typer, httpx, and keyring. Commands use the stored GetBlock
Public API key and print API response data without changing its units or shape.

Install for development:

```powershell
python -m pip install -e ".[dev]"
getblock auth login
```

## Commands

Existing commands: `auth login`, `auth status`, `auth logout`, `me`, and
`tokens list`, `tokens get <id>`, `tokens create`, `tokens delete <id>`,
`tokens rotate <id>`. Run any command with `--help` for its options.

New commands:

```text
getblock dedicated list [--limit 20] [--offset 0] [--protocol ...] [--network ...] [--region ...] [--status ...]
getblock dedicated get <id>
getblock dedicated tokens create <id> --api jsonrpc [--addon ...]
getblock limitless list [--limit 20] [--offset 0] [--protocol ...] [--network ...] [--region ...] [--status ...]
getblock limitless get <id>
getblock limitless tokens create <id> --api json-rpc [--addon ...]
getblock subscription
getblock subscriptions list [--limit 20] [--offset 0] [--product-type ...] [--status ...]
getblock subscriptions get <id>
getblock protocols list [--limit 20] [--offset 0] [--search ...]
getblock protocols get <id>
getblock addons list [--limit 20] [--offset 0] [--search ...] [--protocol ...]
getblock pricing list [--limit 20] [--offset 0] [--search ...]
getblock balance
```

All new commands require authentication. IDs are positional. List defaults are
`limit=20` and `offset=0`; filters are forwarded to the API as supplied. Dedicated
filters combine with AND and are case-insensitive on the server; the API clamps
its limit above 100. The CLI does not add local enum validation or clamping.

Node token creation sends only `api` and `addon`. Omitted `--addon` sends an empty
string (no addon), matching the existing shared-token CLI convention. Use the API
identifier supported by the node; `jsonrpc` and `json-rpc` are not normalized.

`subscription` shows the current plan and accepts `has_plan: false` normally.
`subscriptions get <id>` fetches one subscription. Documented product types are
`plan`, `enterprise_plan`, and `request_package`.

Pricing amounts are whole units of the stated currency. Balance's
`credits.balance_cents` stays in cents. Responses are passed through unchanged.

## Tests

```powershell
python -B -m pytest -q -p no:cacheprovider
```

Tests use `httpx.MockTransport`; a test fixture blocks real HTTP transport.
These are mocked unit tests, not real GetBlock API integration tests.
No `/mcp/v1` functionality is implemented.

## Advanced API (authentication wiring pending)

The Advanced endpoint methods and CLI handlers are implemented and tested with
mocked HTTP responses. **Advanced CLI commands currently stop with a configuration
error and do not make requests.** The supplied contract does not specify the
Advanced base URL, authentication header, or whether the stored Public API key
is valid for this surface. These details must be established before enabling
`get_authenticated_advanced_client()`. No second credential scheme was invented.

Official product examples reference `https://services.getblock.io`, but the
[Wallet Audit example](https://getblock.io/wallet-audit-check/) uses Bearer auth
and the [Wallet Risk example](https://getblock.io/wallet-risk-check/) uses
`x-api-key`. Neither establishes compatibility with the stored Public API key.
The supplied request/response contract takes precedence over differing web examples.

`AdvancedGetBlockClient` accepts an explicitly configured `httpx.Client`; the
caller owns and closes it. It shares low-level request/error handling with the
Public client through `GetBlockHTTPClient`, without inheriting Public endpoints.
The existing `getblock.client.GetBlockAPIError` import remains supported.

Advanced command grammar:

```text
getblock tron-energy price-estimate --resource-type ... --volume ... --duration ...
getblock tron-energy address-status <address>
getblock tron-energy address-activation-estimate
getblock tron-energy orders list [--status ...] [--resource-type ...] [--limit 20] [--offset 0]
getblock tron-energy orders get <id>
getblock tron-energy delegate-energy --target-address ... --volume ... --duration ... --quote-token ... [--yes/-y]
getblock tron-energy delegate-bandwidth --target-address ... --volume ... --duration ... --quote-token ... [--yes/-y]
getblock tron-energy address-activate <address> [--yes/-y]
getblock wallet-audit audit --network ... --address ...
getblock wallet-audit check --network ... --address ...
getblock rug-pull check --network ... --contract-address ...
getblock aml wallet-check --address ... --network ...
getblock aml tx-check --tx ... --network ...
```

All endpoint paths use `/v1/`, without `/api`. Network, duration, and resource
strings pass through unchanged. Order pagination sends the documented defaults;
optional filters are omitted only when `None`. The API's documented order-list
maximum is 100; the client does not guess whether the server clamps or rejects
larger limits. No local enums or additional fields are introduced.

The three TRON state-changing commands require confirmation (default No), unless
`--yes` or `-y` is supplied. Declining or EOF sends no request. Wallet Audit, Rug
Pull, and AML may consume prepaid units or Credits; their command help states
this. No live operations were run during implementation or tests.

Delegation accepts both 200 and 202 and preserves the entire response, including
order IDs. There is no automatic retry or polling of billable operations. AML
responses retain their wrappers and nested detail. HTTP 402 errors display
available `have_cents` and `need_cents` amounts; 500/503 have useful fallbacks.

The test-only hostname `advanced.example.test` is used exclusively with
`httpx.MockTransport`. Passing tests do not establish live API compatibility.
No live Advanced API calls were made, and no funds, credits, or resources were
consumed. This is not live integration testing. MCP remains out of scope.
