import httpx

from getblock.http_client import GetBlockHTTPClient


class AdvancedGetBlockClient(GetBlockHTTPClient):
    """Advanced API endpoints, separate from the Public API client.

    Accept an explicitly configured HTTP client until credential compatibility
    and the authoritative Advanced authentication contract are established.
    """

    def __init__(self, client: httpx.Client):
        # The caller owns the configured client and its lifetime.
        self.client = client

    def estimate_tron_price(self, resource_type: str, volume: int, duration: str):
        payload = {
            "resourceType": resource_type,
            "volume": volume,
            "duration": duration,
        }
        response = self._request("POST", "/v1/tron-energy/price-estimate", json=payload)
        return response.json()

    def get_tron_address_status(self, address: str):
        params = {
            "address": address,
        }
        response = self._request("GET", "/v1/tron-energy/address-status", params=params)
        return response.json()

    def estimate_tron_address_activation(self):
        response = self._request("GET", "/v1/tron-energy/address-activation-estimate")
        return response.json()

    def get_tron_orders(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        resource_type: str | None = None,
    ):
        params = {
            "limit": limit,
            "offset": offset,
            "status": status,
            "resource_type": resource_type,
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._request("GET", "/v1/tron-energy/orders", params=params)
        return response.json()

    def get_tron_order(self, order_id: str):
        response = self._request("GET", f"/v1/tron-energy/orders/{order_id}")
        return response.json()

    def delegate_tron_energy(self, target_address: str, volume: int, duration: str, quote_token: str):
        payload = {
            "target_address": target_address,
            "volume": volume,
            "duration": duration,
            "quote_token": quote_token,
        }
        response = self._request("POST", "/v1/tron-energy/delegate-energy", json=payload)
        return response.json()

    def delegate_tron_bandwidth(self, target_address: str, volume: int, duration: str, quote_token: str):
        payload = {
            "target_address": target_address,
            "volume": volume,
            "duration": duration,
            "quote_token": quote_token,
        }
        response = self._request("POST", "/v1/tron-energy/delegate-bandwidth", json=payload)
        return response.json()

    def activate_tron_address(self, target_address: str):
        payload = {
            "target_address": target_address,
        }
        response = self._request("POST", "/v1/tron-energy/address-activate", json=payload)
        return response.json()

    def audit_wallet(self, network: str, address: str):
        payload = {
            "network": network,
            "address": address,
        }
        response = self._request("POST", "/v1/wallet-audit/audit", json=payload)
        return response.json()

    def check_wallet(self, network: str, address: str):
        payload = {
            "network": network,
            "address": address,
        }
        response = self._request("POST", "/v1/wallet-audit/check", json=payload)
        return response.json()

    def check_rug_pull(self, network: str, contract_address: str):
        payload = {
            "network": network,
            "contract_address": contract_address,
        }
        response = self._request("POST", "/v1/rug-pull/check", json=payload)
        return response.json()

    def check_aml_wallet(self, address: str, network: str):
        payload = {
            "address": address,
            "network": network,
        }
        response = self._request("POST", "/v1/aml/wallet-check", json=payload)
        return response.json()

    def check_aml_transaction(self, tx: str, network: str, asset: str | None = None):
        payload = {
            "tx": tx,
            "network": network,
        }
        if asset is not None:
            payload["asset"] = asset
        response = self._request("POST", "/v1/aml/tx-check", json=payload)
        return response.json()
