import httpx


class GetBlockAPIError(Exception):
    """Error returned when communicating with the GetBlock API."""

    def __init__(self, message: str, status_code: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.api_error_code = None
        self.have_cents: int | None = None
        self.need_cents: int | None = None
        self.upstream_message: str | None = None


class GetBlockHTTPClient:
    """Shared request and error handling for GetBlock API surfaces."""

    def _get_error_message(self, response: httpx.Response, fallback: str) -> str:
        try:
            data = response.json()

            if isinstance(data, dict) and data.get("error"):
                message = str(data["error"] or fallback)
                return message

        except ValueError:
            pass

        return fallback

    def _request(self, method: str, path: str, **kwargs):
        from getblock.ux import current, PreviewReady, CLIError, clean
        from getblock.output import redact
        import typer
        state = current.get()
        pagination = kwargs.pop("pagination", None)
        if getattr(self, "preview", False):
            raise PreviewReady({
                "dry_run": True,
                "api": "advanced" if path.startswith("/v1/") else "public",
                "base_url": self.BASE_URL,
                "method": method,
                "path": path,
                "query": kwargs.get("params", {}),
                "body": redact(kwargs.get("json")),
                "note": "No network request. No server validation or price verification. Credentials omitted.",
            })
        if state and state.verbose and state.output != "json":
            typer.echo(clean(f"{method} {path} (profile={state.profile})", state), err=True)
        def send(arguments):
            try:
                response = self._send(method, path, **arguments)
                if state and method not in ("GET", "HEAD"):
                    state.mutation_succeeded = True
                if response.status_code != 204:
                    try:
                        response.json()
                    except ValueError:
                        raise GetBlockAPIError("GetBlock returned an invalid JSON response.", status_code=response.status_code)
                return response
            except GetBlockAPIError as error:
                response = getattr(self, "last_response", None)
                if response is not None:
                    error.request_id = response.headers.get("x-request-id")
                    try:
                        body = response.json()
                        if isinstance(body, dict) and isinstance(body.get("error"), str):
                            error.api_error_code = body["error"]
                        if path.startswith("/v1/") and isinstance(body, dict) and isinstance(body.get("message"), str):
                            error.upstream_message = body["message"]
                        if response.status_code == 402 and isinstance(body, dict):
                            for field in ("have_cents", "need_cents"):
                                value = body.get(field)
                                if isinstance(value, int) and not isinstance(value, bool):
                                    setattr(error, field, value)
                        if isinstance(body, dict) and isinstance(body.get("request_id"), str):
                            error.request_id = body["request_id"]
                    except ValueError:
                        pass
                if state:
                    error.args = (clean(str(error), state),)
                    if error.upstream_message is not None:
                        error.upstream_message = clean(error.upstream_message, state)
                raise
        if not state or not state.paginate or method != "GET":
            return send(kwargs)
        from getblock.output import COLLECTIONS
        params = dict(kwargs.get("params", {}))
        if pagination == "cursor":
            pages, cursors = [], set()
            if "cursor" in params:
                cursors.add(params["cursor"])
            while True:
                response = send({**kwargs, "params": params})
                data = response.json()
                if not isinstance(data, dict) or not any(isinstance(data.get(k), list) for k in ("items", "addresses")):
                    raise CLIError("Missing collection in cursor response; no partial export was written.")
                pages.append(data)
                cursor = data.get("next_cursor")
                if cursor is None or cursor == "":
                    return httpx.Response(response.status_code, json=pages)
                if not isinstance(cursor, str):
                    raise CLIError("Invalid next_cursor; no partial export was written.")
                if cursor in cursors:
                    raise CLIError("Pagination repeated a cursor; no partial export was written.")
                if state.max_pages and len(pages) >= state.max_pages:
                    raise CLIError("Reached --max-pages before exhaustion; no partial export was written.")
                cursors.add(cursor)
                params["cursor"] = cursor
        if "offset" not in params or "limit" not in params:
            raise CLIError("This endpoint does not support pagination.", 2)
        if params["limit"] <= 0 or params["offset"] < 0:
            raise CLIError("Pagination requires a positive limit and nonnegative offset.", 2)
        pages, fingerprints = [], set()
        import json
        while True:
            response = send({**kwargs, "params": params})
            data = response.json()
            if not isinstance(data, dict):
                raise CLIError("Unexpected pagination response; no partial export was written.")
            rows = next((data[k] for k in COLLECTIONS if isinstance(data.get(k), list)), None)
            if rows is None:
                raise CLIError("Missing collection in pagination response.")
            fingerprint = json.dumps(rows, sort_keys=True)
            if rows and fingerprint in fingerprints:
                raise CLIError("Pagination repeated a page; stopped without a partial export.")
            fingerprints.add(fingerprint)
            pages.append(data)
            total = data.get("total")
            next_offset = params["offset"] + len(rows)
            if not rows or (isinstance(total, int) and next_offset >= total):
                return httpx.Response(response.status_code, json=pages)
            if state.max_pages and len(pages) >= state.max_pages:
                raise CLIError("Reached --max-pages before exhaustion; no partial export was written.")
            params["offset"] = next_offset

    def _send(self, method: str, path: str, **kwargs):
        self.last_response = None
        try:
            from getblock.presentation import waiting
            with waiting():
                response = self.client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise GetBlockAPIError("Request to GetBlock timed out.")
        except httpx.RequestError:
            raise GetBlockAPIError("Unable to connect to GetBlock.")

        self.last_response = response

        if response.status_code == 413:
            raise GetBlockAPIError(
                self._get_error_message(response, "Request body too large (HTTP 413); webhook/address-list bodies have a 5 MiB limit."),
                status_code=413,
            )
        if response.status_code == 402:
            message = self._get_error_message(response, "Insufficient prepaid balance.")
            try:
                data = response.json()
            except ValueError:
                data = {}
            if isinstance(data, dict):
                balances = []
                for field in ("have_cents", "need_cents"):
                    value = data.get(field)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        balances.append(f"{field}={value}")
                if balances:
                    message += " (" + ", ".join(balances) + ")"
            raise GetBlockAPIError(message, status_code=402)
        if response.status_code in (500, 503):
            fallback = (
                "GetBlock encountered an internal error."
                if response.status_code == 500
                else "GetBlock service is temporarily unavailable."
            )
            raise GetBlockAPIError(
                self._get_error_message(response, fallback),
                status_code=response.status_code,
            )

        if response.status_code == 401:
            message = self._get_error_message(response, "Authentication failed. Check your GetBlock API key.")

            raise GetBlockAPIError(
                message,
                status_code=401
            )
        if response.status_code == 404:
            message = self._get_error_message(response, "Requested resource was not found.")
            raise GetBlockAPIError(
                message,
                status_code=404
            )
        if response.status_code == 502:
            message = self._get_error_message(response, "GetBlock service is temporarily unavailable.")
            raise GetBlockAPIError(
                message,
                status_code=502
            )
        if response.status_code == 400:
            message = self._get_error_message(response, "Invalid request or unsupported configuration.")
            raise GetBlockAPIError(
                message,
                status_code=400,
            )
        if response.status_code == 403:
            message = self._get_error_message(response, "Your GetBlock plan does not allow this operation.")
            raise GetBlockAPIError(
                message,
                status_code=403,
            )
        if response.status_code == 429:
            message = self._get_error_message(response, "Too many requests. Please try again later.")
            raise GetBlockAPIError(
                message,
                status_code=429,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            message = self._get_error_message(response, f"GetBlock API returned HTTP: {response.status_code}.")
            raise GetBlockAPIError(
                message,
                status_code=response.status_code
            )

        return response
