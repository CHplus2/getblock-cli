# GetBlock CLI

A Python developer CLI built with Typer, httpx, and keyring. Public API commands
manage account access and discover endpoint configurations. Advanced API client
methods and command workflows are implemented, but their live connection remains
disabled until the authoritative host, authentication header, and credential
compatibility are established. Offline Advanced previews work now.

## Get started

```powershell
python -m pip install -e ".[dev]"
getblock --version
getblock auth login
getblock auth status --check
getblock account show
getblock account plan
getblock account balance
getblock help workflows
```

`account show`, `account plan`, and `account balance` are aliases for `me`,
`subscription`, and `balance`. All original command spellings remain available.
Root help groups account/access, nodes, catalog, and Advanced services.
Command help includes examples, prerequisites, related commands and output notes.

## Output and scripting

Human output is plain text: lists use columns and details use labeled sections.
No ANSI decoration or pager is applied, and identifiers are not truncated.
Credential-bearing fields such as endpoint URLs and quote tokens are redacted in
human output. Missing values are distinguished from zero. Pricing remains in
whole stated-currency units; credit balances remain labeled in cents.

```powershell
getblock tokens list --json
getblock tokens list --output json
getblock tokens list --output tsv --fields id,protocol
$data = getblock tokens list --json | ConvertFrom-Json
$data.tokens | Select-Object id, protocol
```

POSIX shells:

```sh
getblock tokens list --json | jq -r '.tokens[].id'
```

- `--json` / `--output json` returns the complete API response, including wrappers,
  nested data, and any returned endpoint credentials. Treat exports as sensitive.
- JSON selection is explicit: redirecting stdout does not change its schema.
- TSV has no header. It requires named scalar fields; missing/nested fields fail
  without a partial output. Selected values are explicit exports, not redacted.
- Data goes to stdout; diagnostics and prompts go to stderr. JSON errors have
  an `error` object with message, operation, exit code and available status/request ID.
- Human `--verbose` diagnostics show method/path/profile, never auth headers or
  bodies. Verbose and watch progress are suppressed in JSON mode.
- Normal broken pipes exit cleanly. Errors never trigger automatic POST retries.

## Authentication and profiles

```text
getblock auth login
getblock auth login --with-key
getblock auth status
getblock auth status --check
getblock --profile production auth login
getblock --profile production balance
getblock --profile production auth logout
getblock auth status --api advanced
```

Login stores a Public API key in the OS keyring without claiming it was verified.
`--with-key` reads one key from stdin; API keys are not accepted as argv options.
`auth status` inspects configuration without network access; `--check` uses only
Public `GET /api/v1/me`. Status reports the source and verification result without
printing the key. There is no plaintext credential-store fallback.

For CI, inject `GETBLOCK_API_KEY` through the CI secret facility. It overrides the
selected profile's stored Public credential; it is never assumed valid for Advanced.
The `default` profile keeps the original `getblock_api_key` keyring entry; named
profiles have separate entries. Logout removes only the selected stored entry and
reports if an environment credential remains active. Profiles are account names,
not separate GetBlock server environments.

## Configuration

```text
getblock config list --show-origin
getblock config set output json
getblock --profile production config set timeout 30
getblock --timeout 15 protocols list
getblock help configuration
```

Nonsecret settings are stored in `config.json` under `%APPDATA%/getblock` on
Windows or `~/.config/getblock` otherwise. `GETBLOCK_CONFIG_DIR` overrides that
directory. Repository-local configuration is never loaded.

Precedence: explicit flags > `GETBLOCK_OUTPUT` / `GETBLOCK_TIMEOUT` > selected
profile > defaults (`output=table`, `timeout=10` seconds). Profile selection:
`--profile` > `GETBLOCK_PROFILE` > `default`.

Only `output` and `timeout` are accepted settings. Hosts, headers, API keys and
persistent `--yes` are not configurable. Global `--profile`, `--timeout`, and
`--verbose` go before the command; output/workflow flags go after the leaf command.

## Discovery and Public API commands

```text
getblock tokens list
getblock tokens get TOKEN_ID
getblock tokens create --interactive
getblock tokens delete TOKEN_ID
getblock tokens rotate TOKEN_ID
getblock dedicated list
getblock dedicated get NODE_ID
getblock dedicated tokens create NODE_ID --api API [--addon ADDON]
getblock limitless list
getblock limitless get NODE_ID
getblock limitless tokens create NODE_ID --api API [--addon ADDON]
getblock subscriptions list
getblock subscriptions get SUBSCRIPTION_ID
getblock protocols list --search Ethereum
getblock protocols get eth
getblock addons list
getblock pricing list
```

Shared token creation also accepts the original explicit `--protocol`, `--network`,
`--api`, `--mode`, `--region`, and optional `--addon` flags. Guided creation reads
the catalog and offers returned protocol/network/mode/addon/API/region combinations,
then asks before creating the token. Node creation also supports `--interactive`.
It requires a terminal and is not combined with file input or offline previews.
No protocol-specific defaults or identifier normalization are invented.
Node-bound token requests still send only `api` and `addon`; omitted addon is `""`.

No-plan subscription responses are normal. Supported subscription product-type
suggestions are `plan`, `enterprise_plan`, and `request_package`; arbitrary filter
strings still pass through to the API. Completion suggestions are not validation.

## Filtering and pagination

```text
getblock dedicated list --protocol eth --network mainnet --limit 20 --offset 0
getblock tokens list --paginate --max-pages 10 --json
```

Existing documented filters remain available; optional values are omitted only
when `None`. `--limit` remains page size and `--offset` remains the starting offset.
`--paginate` retains filters on every request and advances by actual returned row
count, including when the server clamps page size. JSON pagination returns an
array of complete page responses; human output combines the rows.

Pagination ends on an empty page or the reported total. Repeated pages fail safely.
`--max-pages` bounds requests: reaching it before exhaustion is an error, not a
successful partial export. Failed pagination prints no partial data. Without a
bound, pagination collects all returned pages in memory. Offset-based retrieval
is not a snapshot if server data changes during traversal.

## Request input and offline inspection

Body-based commands expose `--input FILE` or `--input -` for a single JSON object.
Input uses documented API field casing (for example `resourceType`), rejects unknown
fields and wrong scalar types, and conflicts with explicitly supplied body flags.
Positional resource IDs stay positional. It never performs automatic bulk operations.

```powershell
getblock aml wallet-check --input request.json --dry-run --json
Get-Content -Raw request.json | getblock aml wallet-check --input - --dry-run --json
getblock tron-energy delegate-energy --target-address ADDRESS --volume 1 --duration DURATION --quote-token QUOTE --dry-run --json
getblock tokens delete TOKEN_ID --dry-run
```

`--dry-run` uses the same client methods that construct live requests, but stops
before HTTP client creation or credential access. It displays method, path, query,
and redacted body; unknown Advanced base URL is `null`. No network, balance check,
quote validation, price verification, or operation occurs. Preview one page at a
time; it cannot be combined with pagination or interactive catalog discovery.
Local commands such as logout/config set preview their local action instead.

## Safety and exit codes

Token deletion/rotation, TRON delegation/activation, Wallet Audit, Rug Pull, and
AML require confirmation by default. Prompts identify the profile and target,
relevant request inputs, and consequences. Missing Advanced connectivity is
reported before asking for consent. Rotation warns that the old token stops
working immediately. Quote tokens are not echoed in prompts.

In noninteractive execution use `--yes` / `-y`; otherwise the command fails
immediately without a mutation. Declining or interrupting confirmation also fails
without a mutation. No automatic retry of billable requests is performed.

Exit codes: `0` success/preview, `1` operational failure, `2` usage/input error,
`3` cancellation or missing consent, `4` authentication/keyring failure,
`5` watch deadline. See `getblock help exit-codes`.

## Advanced workflows: connection pending

Existing paths and payloads remain `/v1/...` without `/api`. See
`getblock help advanced` for the authentication prerequisite. The separate
`AdvancedGetBlockClient` still accepts a caller-owned configured httpx client.
No new authentication scheme or live-service endpoint has been guessed.

```text
getblock tron-energy price-estimate --resource-type energy --volume VOLUME --duration DURATION --save-quote quote.json
getblock tron-energy delegate-energy --target-address ADDRESS --volume VOLUME --duration DURATION --quote-file quote.json
getblock tron-energy delegate-bandwidth --target-address ADDRESS --volume VOLUME --duration DURATION --quote-token QUOTE
getblock tron-energy address-status ADDRESS
getblock tron-energy address-activation-estimate
getblock tron-energy address-activate ADDRESS
getblock tron-energy orders list
getblock tron-energy orders get ORDER_ID
getblock tron-energy orders watch ORDER_ID --interval 5 --timeout 120
getblock wallet-audit audit --network NETWORK --address ADDRESS
getblock wallet-audit check --network NETWORK --address ADDRESS
getblock rug-pull check --network NETWORK --contract-address ADDRESS
getblock aml wallet-check --network NETWORK --address ADDRESS
getblock aml tx-check --network NETWORK --tx TRANSACTION
```

These live workflows remain unavailable through the CLI pending authentication.
They are covered by mocked tests and can be inspected with `--dry-run`.

A saved quote contains `inputs` and the full `estimate` response, including its
sensitive quote token. Use a private directory (especially on Windows, where
inherited ACLs govern file access). Creation is exclusive and never overwrites an
existing file. `--quote-file` checks resource type, volume and duration locally,
and conflicts with `--quote-token`/`--input`. Server expiry and validity are not
assumed. Plain `--json > file` lacks the input metadata; use `--save-quote`.

Delegation preserves both HTTP 200 and 202 responses and order IDs. Acceptance is
not delivery. Watch polls only order GET requests and limits each request timeout
to remaining watch time. It does not guess terminal meanings for `charged` or
`delivered_uncharged`. Without an explicit condition it observes until timeout
(exit 5). After verifying the actual response schema, supply both `--status-field`
(a dot path) and `--until-status` (an exact value) to stop successfully on your
chosen condition. This does not itself assert that delivery succeeded.

Advanced contract notes:

- `getblock aml tx-check --tx TRANSACTION --network eth --asset usdt --yes --dry-run --json`
  includes the supplied asset string. Omitting `--asset` preserves the existing
  two-field `tx`/`network` request. JSON `--input` also accepts `asset`; when
  present it must be a string. No asset names or nullable semantics are inferred.
- HTTP 402 JSON errors expose integer `error.have_cents` and `error.need_cents`
  when supplied, alongside the existing readable message and `api_error_code`.
  These are also attributes on `GetBlockAPIError`; absent or non-integer values
  remain unset. There is no currency conversion.
- Advanced upstream errors retain their diagnostic as `error.upstream_message`
  separately from `error.api_error_code` and the existing CLI `error.message`.
  Human output adds an `Upstream:` line. Known credentials and quote tokens are
  redacted before rendering. Public error messages and exit codes are preserved.
- Raw `probabilityFraud` JSON is not normalized: strings stay strings and numbers
  stay numbers. The supplied description does not establish that the CLI must
  convert the API's representation.
- Known request constraints remain server-validated: resources are `energy` or
  `bandwidth`, volume has a minimum of 1, and TRON targets match
  `^T[A-Za-z0-9]{33}$`. No duration/network enums are inferred.

The schema extract still hides some required/nullable metadata and the inner
counterparty-object definitions. Those details are not guessed. It also does
not establish the Advanced host/authentication contract; live Advanced access
remains unavailable. Contract coverage uses mocked responses, including the
supplied complete AML address report, not live integration tests.

## Notify: webhooks and address lists

These Public API commands use the existing profile/keyring or `GETBLOCK_API_KEY`
authentication, timeout, `--json`, `--output tsv --fields ...`, and offline
`--dry-run` options. IDs are positional. No additional credentials are required.

All commands below use real account resources unless `--dry-run` is present.
`WEBHOOK_ID` and `LIST_ID` are placeholders, not existing resources.

```sh
getblock webhooks limits
getblock webhooks list --paginate --json
getblock webhooks get WEBHOOK_ID
getblock webhooks create --input webhook.json --dry-run --json
getblock webhooks update WEBHOOK_ID --input patch.json --dry-run --json
getblock webhooks pause WEBHOOK_ID --dry-run
getblock webhooks resume WEBHOOK_ID --dry-run
getblock webhooks secret rotate WEBHOOK_ID --dry-run --json
getblock webhooks test WEBHOOK_ID --dry-run
getblock webhooks deliveries WEBHOOK_ID --status retrying --status failed_terminal --json
getblock webhooks stats WEBHOOK_ID
getblock webhooks addresses WEBHOOK_ID --output tsv --fields address
getblock webhooks delete WEBHOOK_ID --dry-run

getblock address-lists list --paginate --json
getblock address-lists create --input list.json --dry-run --json
getblock address-lists get LIST_ID
getblock address-lists rename LIST_ID --name "Treasury wallets" --dry-run
getblock address-lists entries list LIST_ID --paginate --json
getblock address-lists entries add LIST_ID --input addresses.json --dry-run
getblock address-lists entries replace LIST_ID --input addresses.json --dry-run
getblock address-lists entries remove LIST_ID --input addresses.json --dry-run
getblock address-lists delete LIST_ID --dry-run
```

`--input FILE` reads a UTF-8 JSON object; `--input -` reads stdin. For example:

```powershell
Get-Content -Raw webhook.json | getblock webhooks create --input - --dry-run --json
```

An illustrative `webhook.json` (replace the receiver URL before executing):

```json
{
  "chain": "eth",
  "trigger_type": "address_activity",
  "phases": ["confirmed"],
  "target_url": "https://hooks.example.io/getblock",
  "addresses": ["0x742d35cc6634c0532925a3b844bc454e4438f44e"]
}
```

Optional fields include `name`, `network`, `filters`, `confirm_depth`, `batching`
and `list_refs`. JSON input preserves nested filter trees and batching objects.
The CLI checks documented top-level keys and required key presence; the server
validates values, nested grammar, chain/network support, and plan caps. It does
not normalize addresses, fill omitted fields, or infer defaults from examples.
Unknown PATCH keys, including `chain`, `network` and `trigger_type`, are refused.
The supplied schema's field details are partially collapsed, so the CLI does
not impose undocumented enum sets or validation limits.

For `patch.json`, `{"name":"Treasury activity"}` changes only the name.
`{"confirm_depth":null}` resets depth to the chain default; omitting it leaves
it unchanged. `{"addresses":[]}` clears inline addresses, but the server rejects
a result with no filter condition (`filter_would_be_empty`); supply a remaining
`filters` tree in the same patch if needed. Empty arrays and explicit null are
forwarded unchanged. Do not copy a returned `src: "sugar"` filter leaf back into
`filters`: this marker is reserved by the API.

For `list.json`, use `{"name":"Treasury wallets","addresses":[]}`; addresses
may be omitted on creation. For `addresses.json`, use `{"addresses":["0x742d35cc6634c0532925a3b844bc454e4438f44e"]}`.
Replacing with `{"addresses":[]}` clears a list. Adding ignores existing entries;
removing ignores absent entries. These changes affect webhooks referencing the
list. Renaming also accepts `--input` with `{"name":"Cold wallets"}` instead of
`--name`; do not combine both.

Notify uses **cursor pagination**: `--limit` defaults to 50 (server maximum 200),
except deliveries, which defaults to 100 (server maximum 999). Larger values are
forwarded for the server to clamp. Pass an opaque `next_cursor` through `--cursor`,
or use `--paginate`. JSON pagination returns an array of unchanged page objects;
TSV/human output combines the rows. Repeated cursors, malformed responses, failed
pages, and `--max-pages` reached before completion fail without partial stdout.
No offset or total-count assumption is applied. Addresses use the scalar TSV
field `address`; JSON retains the original array of strings.

Delivery filters are `--from` (inclusive RFC 3339), `--to` (exclusive RFC 3339),
and repeatable/comma-separated `--status`. Documented statuses are `delivered`,
`retrying`, `failed_terminal`, and `replayed`. The log contains retries/failures
and test events; successful production deliveries are not logged. Under mass
failure it is sampled, so use statistics for exact totals. Rates can be null
while totals remain available. A test event's HTTP 202 means **queued**, not
delivered; it affects statistics and repeated failures can cause auto-pause.
There are no automatic POST retries, including on `test_event_unavailable`:
a timed-out test may still be delivered, and retrying creates another event.

Creation and secret rotation return a signing secret only once. Human output
redacts it; use `--json` to capture the complete response securely when executing
these commands. TSV explicitly selecting `secret` also exposes it. Diagnostics
never log response bodies. Routine rotation sends no body and allows the previous
secret for 24 hours. `--expire-previous` sends `{"expire_previous":true}` and
expires it immediately. A second rotation during overlap retires the older
secret immediately. Rotation, deletion, entry replacement and entry removal
require confirmation, or `--yes` in scripts. Previews require no confirmation.
Deletion is irreversible; deleting a webhook also removes its stats and log.
An address list still referenced by a webhook cannot be deleted (`list_in_use`).
Pausing retains the plan slot; resuming remains subject to plan and balance checks.

JSON errors go to stderr with the HTTP status, API error code when supplied, and
request ID. Plain-text gateway 413 errors report the documented 5 MiB body limit
without attempting to parse JSON or echoing the gateway page. `webhooks limits`
is advisory; creation remains authoritative if a plan changes between calls.

Implemented REST/client inventory (all paths start with `/api/v1`):

```text
GET    /webhooks                      get_webhooks
POST   /webhooks                      create_webhook
GET    /webhooks/limits               get_webhook_limits
GET    /webhooks/{id}                 get_webhook
PATCH  /webhooks/{id}                 update_webhook
DELETE /webhooks/{id}                 delete_webhook
POST   /webhooks/{id}/pause           pause_webhook
POST   /webhooks/{id}/resume          resume_webhook
POST   /webhooks/{id}/secret/rotate   rotate_webhook_secret
POST   /webhooks/{id}/test            send_webhook_test
GET    /webhooks/{id}/deliveries      get_webhook_deliveries
GET    /webhooks/{id}/stats           get_webhook_stats
GET    /webhooks/{id}/addresses       get_webhook_addresses
GET    /address-lists                get_address_lists
POST   /address-lists                create_address_list
GET    /address-lists/{id}            get_address_list
PATCH  /address-lists/{id}            rename_address_list
DELETE /address-lists/{id}            delete_address_list
GET    /address-lists/{id}/entries    get_address_list_entries
POST   /address-lists/{id}/entries    add_address_list_entries
PUT    /address-lists/{id}/entries    replace_address_list_entries
POST   /address-lists/{id}/entries/remove  remove_address_list_entries
```

Coverage is mocked unit testing with `httpx.MockTransport`, not live integration
testing against GetBlock. `/mcp/v1` is intentionally unimplemented. Schemas are
data models, not CLI commands.

## Shell support

```text
getblock --install-completion
getblock --show-completion
getblock help shell
```

Typer supplies Bash, Zsh, Fish, PowerShell/pwsh completion. Documented static values
are suggested without network requests. No dynamic API-backed completion, built-in
jq interpreter, generic HTTP command, or plugin framework has been added.

## Compatibility and implementation

Existing command names, Public host/authentication, endpoint methods, API payloads
and response parsing remain. Shared UX lives in `ux.py`, rendering in `output.py`,
settings in `config.py`, and multi-step workflows in `workflows.py`. API request
construction remains in the client classes; previews reuse it.

Intentional UX changes: default output is readable text, JSON must be requested
explicitly, cancellation has a nonzero exit code, missing auth exits 4, and paid
audit calls require consent. Existing CLI tests were updated for these contracts;
client-level endpoint tests remain in place. No implementation from GitHub CLI or
HTTPie was copied.

## Tests

```powershell
python -B -m pytest -q -p no:cacheprovider
```

Tests use `httpx.MockTransport`, block real HTTP transport, and isolate CLI settings
from the user's environment. No live Advanced API calls, purchases, delegations,
activations or audit/AML operations were made. No funds, credits or resources were
consumed. These are mocked unit tests, not live integration tests. MCP is out of scope.

## Interactive navigation

Run `getblock interactive` in a terminal to navigate numbered menus using Enter.
The first version covers Account (show, balance, subscription), Protocols and
Tokens (list and select an item to inspect). Results return to navigation;
Back, Home and Exit are available, and collection menus offer pagination.
Equivalent commands are displayed so you can learn commands for scripts.

`getblock --profile production interactive` uses that account profile and the
existing credential lookup. Authenticate beforehand with `getblock auth login`.
The menu uses readable, redacted output even if your profile defaults to JSON.
It does not perform mutations or billable Advanced operations. Advanced live
access remains unavailable pending authentication documentation.

Bare `getblock` and existing commands are unchanged. Interactive mode requires
TTY input; redirected/piped input is rejected before reading credentials or
making requests. Use direct commands with `--json` for automation. Exit ends
normally; Ctrl+C/EOF cancels with the existing cancellation exit code.
