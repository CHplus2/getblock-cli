# GetBlock CLI

A Python developer CLI built with Typer, httpx, and keyring. Public API commands
manage account access and discover endpoint configurations. Advanced commands use
https://services.getblock.io with a separately configured Bearer credential.
Public credentials are never reused for Advanced requests automatically. These
connections are covered by mocked tests; live Advanced integration remains unverified.

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

## Developer workflows

```sh
getblock doctor
getblock doctor --api both --check-network --json
getblock setup
getblock webhooks create --generate-input
getblock webhooks create --input webhook.json --validate-only --json
getblock endpoints check --token-id TOKEN_ID
getblock endpoints request --token-id TOKEN_ID --input rpc.json --dry-run --json
getblock tokens list --json --jq '.tokens[].id'
getblock webhooks deliveries WEBHOOK_ID --watch --interval 5 --timeout 60 --json
```

`doctor` defaults to offline Public diagnosis. `--api both` includes Advanced;
`--check-network` performs only read-only authentication checks for configured
credentials. It reports failures with fixes, exits 1 when any check fails, and
can diagnose malformed configuration. Its JSON report is on stdout even on a
failed diagnosis. Keyring access can still prompt through the operating system.

`setup` is a terminal-only Public onboarding flow: sign in if needed, verify
account access, choose a supported token configuration, confirm creation, and
show the equivalent command. Running that command again creates another token.
It uses the selected profile and existing environment-credential precedence.

Body commands offer `--generate-input` and `--validate-only`. Generated JSON
contains placeholders, not a ready-to-submit configuration. Replace them first.
Local validation reuses request construction but performs no HTTP requests,
credential lookup, file output or mutations. It checks only the constraints the
CLI implements; server-side enum values, nested Notify grammar, quotas and other
business rules remain server-validated. Positional IDs are still required for
resource-specific commands. Endpoint templates also require `--token-id`.

Endpoint commands resolve the selected token's returned `endpoint` field; they
never construct an endpoint URL from its resource ID. URLs must be HTTPS on a
GetBlock subdomain, without user information, custom ports or fragments. RPC
requests never receive management API authorization headers, follow redirects,
or retry automatically. `check` currently supports `protocol=eth` and sends one
documented `eth_blockNumber` request, which may consume quota. Other chains can
use `request` with their documented JSON-RPC payload. Requests require confirmation
or `--yes` because arbitrary methods may change blockchain state. Only single
JSON-RPC 2.0 objects with request IDs are supported; no batches or notifications.
Transport and RPC errors exit nonzero. An endpoint preview performs no token
lookup, so it cannot verify the endpoint or protocol.
Reference: [GetBlock access tokens and Ethereum example](https://docs.getblock.io/getting-started/authentication-with-access-tokens).

`--jq` requires the external jq executable on PATH and JSON output. The CLI
checks availability and syntax before making requests, then passes the complete
JSON result to jq over stdin without a shell. Paginated input retains the array
of complete pages. Output consists of compact JSON values, one per line; strings
remain quoted. Query failures emit no partial query output. A runtime query error
after a mutation reports that the server accepted the operation. Webhook creation
and rotation require `--save-secret` when filtering so a query cannot discard the
one-time signing secret. Reference: [jq manual](https://jqlang.org/manual/).

Delivery `--watch` polls the first page and emits only changed page snapshots;
JSON mode produces JSON Lines, not one JSON document. It exits 5 at the deadline
and may already have emitted snapshots. It cannot combine with cursor pagination,
TSV, jq or dry-run. This is not a complete event stream: logs may be sampled and
successful production deliveries are omitted. Automatic `webhooks test --wait`
is intentionally not added: the supplied contract has not established reliable
test-event-to-delivery correlation. Use `webhooks test` once, inspect delivery
snapshots, and use statistics for totals; the CLI never resends tests automatically.

## Output and scripting

Human output uses terminal-aware colors: lists use columns and details use labeled
sections. Use --color never or NO_COLOR for plain text. No pager is applied, and identifiers are not truncated.
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
- TSV has no header. It requires scalar fields (including dot paths such as data.id); missing fields or selected objects/arrays fail
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
getblock auth login --api advanced
getblock auth status --api advanced --check
getblock auth logout --api advanced
```

Login stores the selected API key in the OS keyring without claiming it was verified.
`--with-key` reads one key from stdin; API keys are not accepted as argv options.
`auth status` inspects configuration without network access; `--check` uses only
Public `GET /api/v1/me`, or Advanced `GET /v1/tron-energy/orders?limit=1&offset=0`.
Advanced verification establishes orders-read access, not all service permissions.
Status reports the source and verification result without
printing the key. There is no plaintext credential-store fallback.

For CI, inject `GETBLOCK_API_KEY` through the CI secret facility. It overrides the
selected profile's stored Public credential; it is never assumed valid for Advanced.
Advanced uses `GETBLOCK_ADVANCED_API_KEY` or its own per-profile keyring entry.
Both services use Bearer headers, but key compatibility is not assumed. Obtain an
Advanced credential from the service administrator; the supplied docs describe
issuance through an Internal API, which this CLI does not call.
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
and redacted body; Advanced previews show `https://services.getblock.io`. No network, balance check,
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

## Advanced workflows

Existing paths and payloads remain `/v1/...` without `/api`. Run
`getblock auth login --api advanced` or set `GETBLOCK_ADVANCED_API_KEY`.
The supplied production contract specifies `https://services.getblock.io` and
`Authorization: Bearer KEY`. Redirects are not followed. The separate
`AdvancedGetBlockClient` also accepts a caller-owned configured httpx client.

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

These workflows require an explicitly configured Advanced credential. They are
covered by mocked tests and can be inspected with `--dry-run`. No live Advanced
requests have been used to verify this implementation.

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
not establish compatibility between Public and Advanced credentials; they remain
separate. Host and Bearer format come from the subsequently supplied Servers and
authentication description. Contract coverage uses mocked responses, including the
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
requires `--save-secret FILE`; alternatively explicitly choose `--json` or TSV
with `--fields secret` to capture it yourself. Existing files are never overwritten.
The destination is reserved before the request, with POSIX mode 0600 or a protected
Windows DACL granting the current user and any restricted-process identities access.
No inherited broad groups are granted. A failed request/write may leave an empty
or partial private file; inspect it and choose a new destination before retrying.
`--dry-run` never creates the file. Raw JSON still includes the secret if requested.

```sh
getblock webhooks create --input webhook.json --save-secret webhook-secret.txt
getblock webhooks secret rotate WEBHOOK_ID --save-secret new-secret.txt --yes
```

These examples perform live mutations when run with valid credentials. Diagnostics
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

Run `getblock interactive` and choose a number. Account offers identity, balance
and subscription. Protocols, Tokens, Webhooks, Address lists, Dedicated nodes
and Limitless nodes offer one selectable list instead of separate List/Inspect
flows. Breadcrumbs show your location. Selecting an item opens details; Back
restores the cached page. Next/Previous pages, Refresh, Home and Exit are available.
Filtering matches names or IDs on the current page only; it does not claim to
search the whole account. Refresh reloads from the first page.

Equivalent commands are displayed, including a selected `--profile`. Login uses
the existing hidden prompt and keyring storage, and authentication failures offer
Sign in. An environment key still takes precedence over a stored key.
The menu uses readable, redacted output even if the profile defaults to JSON.
Resource browsing is read-only; Login explicitly changes stored credentials.
Advanced commands require a separately configured credential; use `getblock auth login --api advanced`.

Bare `getblock` and existing command paths are unchanged. Interactive mode requires
TTY input; use direct commands for scripts. Exit ends normally; Ctrl+C/EOF cancels
with the existing cancellation exit code.

## Terminal presentation and safe automation

Use `getblock --color auto|always|never COMMAND`. Auto enables color only on a
supported terminal; `NO_COLOR` takes precedence over always. JSON/TSV output is
never decorated. Headings, success labels, warnings, errors and command hints use
restrained styles. API values are literal text, never Rich markup. Wide tables
switch to stacked details on narrow terminals to preserve complete identifiers.
A transient loading indicator appears only for human terminal requests on stderr.

TSV accepts nested scalar fields, for example:

```sh
getblock tron-energy orders get ORDER_ID --output tsv --fields data.id,data.status
```

For list responses, fields are relative to each item as before. JSON retains the
original response. If a mutation was accepted but decoding, saving or formatting
fails, the error explicitly says the server accepted it and advises inspection
before retrying. JSON errors include `operation_succeeded: true`. This is not a
claim of delivery/completion for HTTP 202 operations.

Resource identifiers are kept in a single URL path segment. IDs containing URL
separators, traversal, control characters, or encoded equivalents are rejected
before HTTP; ordinary identifiers are encoded without changing their spelling.
Endpoint methods, field names and query parameters are unchanged.

## Reproducible development and CI

Install the pinned development dependency set:

```sh
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python -B -m pytest -q -p no:cacheprovider
python -m build --no-isolation
```

Typer is pinned because this version vendors Click and the error adapter relies
on that interface. Update the lock and dependency bounds together with tests.
The lock includes platform-specific keyring dependencies; these are version pins,
not a cryptographic dependency-integrity lock.

The GitHub Actions matrix covers Python 3.10–3.14 on Windows, Linux and macOS. It
builds a wheel, installs it, copies tests outside the repository and verifies the
installed command's help/version. Tests block live HTTP. Cross-platform CI results
must be checked after the workflow runs; configuring the matrix is not evidence
that every runner has passed. Built wheels exclude bytecode/cache files.
