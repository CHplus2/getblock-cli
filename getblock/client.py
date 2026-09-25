import httpx

class GetBlockAPIError(Exception):
    """Error returned when communicating with the GetBlock API."""

    def __init__(self, message: str, status_code: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id

class GetBlockClient:
    BASE_URL = "https://public-api.getblock.io"

    def __init__(self, api_key: str):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=10.0,
        )

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

    def get_me(self):
        response = self._request("GET", "/api/v1/me")
        return response.json()

    def get_tokens(
        self,
        limit: int = 20,
        offset: int = 0,
        name: str | None = None,
        protocol: str | None = None,
        network: str | None = None,
        region: str | None = None,
        namespace: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "name": name,
            "protocol": protocol,
            "network": network,
            "region": region,
            "namespace": namespace,
        }

        params = {
            key: value
            for key, value in params.items()
            if value is not None
        }

        response = self._request("GET", "/api/v1/tokens", params=params)
        return response.json()

    def get_token(self, token_id: str):
        response = self._request("GET", f"/api/v1/tokens/{token_id}")
        return response.json()

    def create_token(
        self,
        protocol: str,
        network: str,
        api: str,
        mode: str,
        region: str,
        addon: str
    ):
        payload = {
            "protocol": protocol,
            "network": network,
            "api": api,
            "mode": mode,
            "region": region,
            "addon": addon
        }

        response = self._request("POST", "/api/v1/tokens", json=payload)
        return response.json()

    def delete_token(self, token_id: str):
        self._request(
            "DELETE",
            f"/api/v1/tokens/{token_id}",
        )

    def rotate_token(self, token_id: str):
        response = self._request(
            "POST",
            f"/api/v1/tokens/{token_id}/rotate",
        )

        return response.json()
    