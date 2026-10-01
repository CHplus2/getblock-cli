import httpx


class GetBlockAPIError(Exception):
    """Error returned when communicating with the GetBlock API."""

    def __init__(self, message: str, status_code: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


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
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise GetBlockAPIError("Request to GetBlock timed out.")
        except httpx.RequestError:
            raise GetBlockAPIError("Unable to connect to GetBlock.")

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
