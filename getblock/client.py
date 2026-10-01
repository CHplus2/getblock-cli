import httpx

from getblock.http_client import GetBlockAPIError, GetBlockHTTPClient


class GetBlockClient(GetBlockHTTPClient):
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

    def get_dedicated_nodes(
        self,
        limit: int = 20,
        offset: int = 0,
        protocol: str | None = None,
        network: str | None = None,
        region: str | None = None,
        status: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "protocol": protocol,
            "network": network,
            "region": region,
            "status": status,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/dedicated", params=params)
        return response.json()

    def get_dedicated_node(self, node_id: str):
        response = self._request("GET", f"/api/v1/dedicated/{node_id}")
        return response.json()

    def create_dedicated_token(
        self,
        node_id: str,
        api: str,
        addon: str = "",
    ):
        payload = {"api": api, "addon": addon}
        response = self._request("POST", f"/api/v1/dedicated/{node_id}/tokens", json=payload)
        return response.json()

    def get_limitless_nodes(
        self,
        limit: int = 20,
        offset: int = 0,
        protocol: str | None = None,
        network: str | None = None,
        region: str | None = None,
        status: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "protocol": protocol,
            "network": network,
            "region": region,
            "status": status,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/limitless", params=params)
        return response.json()

    def get_limitless_node(self, node_id: str):
        response = self._request("GET", f"/api/v1/limitless/{node_id}")
        return response.json()

    def create_limitless_token(
        self,
        node_id: str,
        api: str,
        addon: str = "",
    ):
        payload = {"api": api, "addon": addon}
        response = self._request("POST", f"/api/v1/limitless/{node_id}/tokens", json=payload)
        return response.json()

    def get_subscription(self):
        response = self._request("GET", "/api/v1/subscription")
        return response.json()

    def get_subscriptions(
        self,
        limit: int = 20,
        offset: int = 0,
        product_type: str | None = None,
        status: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "product_type": product_type,
            "status": status,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/subscriptions", params=params)
        return response.json()

    def get_subscription_by_id(self, subscription_id: str):
        response = self._request("GET", f"/api/v1/subscriptions/{subscription_id}")
        return response.json()

    def get_protocols(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/protocols", params=params)
        return response.json()

    def get_protocol(self, protocol_id: str):
        response = self._request("GET", f"/api/v1/protocols/{protocol_id}")
        return response.json()

    def get_addons(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        protocol: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "protocol": protocol,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/addons", params=params)
        return response.json()

    def get_pricing(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/api/v1/pricing", params=params)
        return response.json()

    def get_balance(self):
        response = self._request("GET", "/api/v1/balance")
        return response.json()
