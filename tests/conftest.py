import httpx
import pytest

from getblock import cli
from getblock.client import GetBlockClient


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Tests must use httpx.MockTransport, never the real network")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture
def mock_client(monkeypatch):
    clients = []
    original_client = httpx.Client

    def make(handler):
        def transport_client(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return original_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", transport_client)
        client = GetBlockClient("fake-api-key")
        clients.append(client.client)
        monkeypatch.setattr(cli, "get_api_key", lambda: "fake-api-key")
        monkeypatch.setattr(cli, "GetBlockClient", lambda api_key: client)
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def advanced_client(monkeypatch):
    from getblock.advanced_client import AdvancedGetBlockClient

    clients = []

    def make(handler):
        transport = httpx.Client(
            base_url="https://advanced.example.test",
            transport=httpx.MockTransport(handler),
        )
        clients.append(transport)
        client = AdvancedGetBlockClient(transport)
        monkeypatch.setattr(cli, "get_authenticated_advanced_client", lambda: client)
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture(autouse=True)
def isolate_cli_configuration(monkeypatch):
    """Never consult a developer's credentials or persisted CLI preferences."""
    import tempfile
    import uuid
    from pathlib import Path

    for name in ("GETBLOCK_API_KEY", "GETBLOCK_ADVANCED_API_KEY", "GETBLOCK_PROFILE", "GETBLOCK_OUTPUT", "GETBLOCK_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cli, "get_advanced_api_key", lambda profile="default": None)
    monkeypatch.setenv("GETBLOCK_CONFIG_DIR", str(Path(tempfile.gettempdir()) / ("getblock-config-" + uuid.uuid4().hex)))


@pytest.fixture
def artifact_dir():
    import tempfile, uuid, shutil
    from pathlib import Path
    root=Path(tempfile.gettempdir()).resolve()
    path=root/('getblock-private-test-'+uuid.uuid4().hex)
    path.mkdir(mode=0o777)
    try:
        yield path
    finally:
        assert path.resolve().parent==root
        shutil.rmtree(path)
