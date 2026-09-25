import json
import httpx

from getblock.client import GetBlockClient, GetBlockAPIError

def make_client(handler):
    client = GetBlockClient("fake-api-key")

    client.client = httpx.Client(
        base_url=client.BASE_URL,
        transport=httpx.MockTransport(handler),
        headers={
            "Authorization": "Bearer fake-api-key",
            "Accept": "application/json",
        },
    )

    return client

def test_get_me():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path =="/api/v1/me"
        assert request.headers["Authorization"] == "Bearer fake-api-key"

        return httpx.Response(
            200,
            json={
                "user_id": "test-user-id"
            },
        )

    client = make_client(handler)

    data = client.get_me()

    assert data["user_id"] == "test-user-id"

def test_list_tokens():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/tokens"

        params = httpx.QueryParams(request.url.query)

        assert params["limit"] == "10"
        assert params["offset"] == "0"
        assert params["protocol"] == "eth"
        assert params["network"] == "mainnet"

        return httpx.Response(
            200,
            json={
                "total": 1,
                "limit": 10,
                "offset": 0,
                "tokens": [
                    {
                        "id": "abc123",
                        "protocol": "eth",
                        "network": "mainnet"
                    }
                ]
            }
        )

    client = make_client(handler)

    data = client.get_tokens(
        limit=10,
        protocol="eth",
        network="mainnet",
    )

    assert data["total"] == 1
    assert data["tokens"][0]["id"] == "abc123"

def test_unauthorized():
    def handler(request):
        return httpx.Response(
            401,
            json={
                "error": "missing user identity",
                "request_id": "test-request-123",
            },
        )

    client = make_client(handler)

    try:
        client.get_me()
        assert False, "Expected GetBlockAPIError"

    except GetBlockAPIError as error:
        assert error.status_code == 401
        assert str(error) == "missing user identity"   

def test_create_token():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/tokens"

        payload = json.loads(request.content)

        assert payload == {
            "protocol": "eth",
            "network": "mainnet",
            "api": "json-rpc",
            "mode": "archive",
            "region": "eu-central-1",
            "addon": "",
        }

        return httpx.Response(
            201,
            json={
                "id": "new-token-id",
                "protocol": "eth",
                "network": "mainnet",
                "endpoint": "https://go.getblock.io/new-token-id",
            },
        )

    client = make_client(handler)

    data = client.create_token(
        protocol="eth",
        network="mainnet",
        api="json-rpc",
        mode="archive",
        region="eu-central-1",
        addon="",
    )

    assert data["id"] == "new-token-id"

def test_delete_token():
    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/tokens/abc123"

        return httpx.Response(204)

    client = make_client(handler)

    result = client.delete_token("abc123")

    assert result is None

def test_rotate_token():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/tokens/abc123/rotate"

        return httpx.Response(
            201,
            json={
                "id": "replacement-token-id",
                "endpoint": "https://go.getblock.io/replacement-token-id",
            },
        )

    client = make_client(handler)

    data = client.rotate_token("abc123")

    assert data["id"] == "replacement-token-id"
    assert data["endpoint"] == (
        "https://go.getblock.io/replacement-token-id"
    )