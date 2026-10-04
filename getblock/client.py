from getblock.paths import path_segment
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
        response = self._request("GET", f"/api/v1/tokens/{path_segment(token_id)}")
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
            f"/api/v1/tokens/{path_segment(token_id)}",
        )

    def rotate_token(self, token_id: str):
        response = self._request(
            "POST",
            f"/api/v1/tokens/{path_segment(token_id)}/rotate",
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
        response = self._request("GET", f"/api/v1/dedicated/{path_segment(node_id)}")
        return response.json()

    def create_dedicated_token(
        self,
        node_id: str,
        api: str,
        addon: str = "",
    ):
        payload = {"api": api, "addon": addon}
        response = self._request("POST", f"/api/v1/dedicated/{path_segment(node_id)}/tokens", json=payload)
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
        response = self._request("GET", f"/api/v1/limitless/{path_segment(node_id)}")
        return response.json()

    def create_limitless_token(
        self,
        node_id: str,
        api: str,
        addon: str = "",
    ):
        payload = {"api": api, "addon": addon}
        response = self._request("POST", f"/api/v1/limitless/{path_segment(node_id)}/tokens", json=payload)
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
        response = self._request("GET", f"/api/v1/subscriptions/{path_segment(subscription_id)}")
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
        response = self._request("GET", f"/api/v1/protocols/{path_segment(protocol_id)}")
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

    def get_webhooks(self, limit: int = 50, cursor: str | None = None):
        return self._cursor_page("/api/v1/webhooks", limit, cursor)

    def create_webhook(self, body: dict):
        """Forward the documented JSON body without adding optional defaults."""
        return self._request("POST", "/api/v1/webhooks", json=body).json()

    def get_webhook_limits(self):
        return self._request("GET", "/api/v1/webhooks/limits").json()

    def get_webhook(self, webhook_id: str):
        return self._request("GET", f"/api/v1/webhooks/{path_segment(webhook_id)}").json()

    def update_webhook(self, webhook_id: str, body: dict):
        """Preserve absent keys, explicit null and empty arrays exactly."""
        return self._request("PATCH", f"/api/v1/webhooks/{path_segment(webhook_id)}", json=body).json()

    def delete_webhook(self, webhook_id: str):
        self._request("DELETE", f"/api/v1/webhooks/{path_segment(webhook_id)}")

    def pause_webhook(self, webhook_id: str):
        return self._request("POST", f"/api/v1/webhooks/{path_segment(webhook_id)}/pause").json()

    def resume_webhook(self, webhook_id: str):
        return self._request("POST", f"/api/v1/webhooks/{path_segment(webhook_id)}/resume").json()

    def rotate_webhook_secret(self, webhook_id: str, expire_previous: bool | None = None):
        arguments = {} if expire_previous is None else {"json": {"expire_previous": expire_previous}}
        return self._request("POST", f"/api/v1/webhooks/{path_segment(webhook_id)}/secret/rotate", **arguments).json()

    def send_webhook_test(self, webhook_id: str):
        """202 queues an event; it does not establish successful delivery."""
        return self._request("POST", f"/api/v1/webhooks/{path_segment(webhook_id)}/test").json()

    def get_webhook_deliveries(
        self, webhook_id: str, limit: int = 100, cursor: str | None = None,
        from_time: str | None = None, to_time: str | None = None,
        status: list[str] | None = None,
    ):
        return self._cursor_page(f"/api/v1/webhooks/{path_segment(webhook_id)}/deliveries", limit, cursor,
                                 **{"from": from_time, "to": to_time, "status": status})

    def get_webhook_stats(self, webhook_id: str):
        return self._request("GET", f"/api/v1/webhooks/{path_segment(webhook_id)}/stats").json()

    def get_webhook_addresses(self, webhook_id: str, limit: int = 50, cursor: str | None = None):
        return self._cursor_page(f"/api/v1/webhooks/{path_segment(webhook_id)}/addresses", limit, cursor)

    def get_address_lists(self, limit: int = 50, cursor: str | None = None):
        return self._cursor_page("/api/v1/address-lists", limit, cursor)

    def create_address_list(self, body: dict):
        return self._request("POST", "/api/v1/address-lists", json=body).json()

    def get_address_list(self, list_id: str):
        return self._request("GET", f"/api/v1/address-lists/{path_segment(list_id)}").json()

    def rename_address_list(self, list_id: str, name: str):
        return self._request("PATCH", f"/api/v1/address-lists/{path_segment(list_id)}", json={"name": name}).json()

    def delete_address_list(self, list_id: str):
        self._request("DELETE", f"/api/v1/address-lists/{path_segment(list_id)}")

    def get_address_list_entries(self, list_id: str, limit: int = 50, cursor: str | None = None):
        return self._cursor_page(f"/api/v1/address-lists/{path_segment(list_id)}/entries", limit, cursor)

    def add_address_list_entries(self, list_id: str, addresses: list[str]):
        return self._request("POST", f"/api/v1/address-lists/{path_segment(list_id)}/entries", json={"addresses": addresses}).json()

    def replace_address_list_entries(self, list_id: str, addresses: list[str]):
        return self._request("PUT", f"/api/v1/address-lists/{path_segment(list_id)}/entries", json={"addresses": addresses}).json()

    def remove_address_list_entries(self, list_id: str, addresses: list[str]):
        return self._request("POST", f"/api/v1/address-lists/{path_segment(list_id)}/entries/remove", json={"addresses": addresses}).json()

    def _cursor_page(self, path, limit, cursor, **filters):
        params = {key: value for key, value in {"limit": limit, "cursor": cursor, **filters}.items()
                  if value is not None}
        return self._request("GET", path, params=params, pagination="cursor").json()
