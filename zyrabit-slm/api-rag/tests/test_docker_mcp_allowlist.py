from unittest.mock import MagicMock

from app.infrastructure.mcp.docker_mcp_client import (
    DockerDiagnosticClient,
    container_name_allowed,
    parse_container_allowlist,
)


def test_default_allowlist_is_zyrabit_prefix():
    assert parse_container_allowlist(None) == ["zyrabit-*"]
    assert container_name_allowed("zyrabit-api", ["zyrabit-*"])
    assert container_name_allowed("/zyrabit-db", ["zyrabit-*"])
    assert not container_name_allowed("unrelated-redis", ["zyrabit-*"])


def test_custom_allowlist_patterns():
    patterns = parse_container_allowlist("zyrabit-api, other-*")
    assert patterns == ["zyrabit-api", "other-*"]
    assert container_name_allowed("zyrabit-api", patterns)
    assert container_name_allowed("other-worker", patterns)
    assert not container_name_allowed("zyrabit-engine", patterns)


def _client_with_containers(names: list[str], allowlist: list[str]) -> DockerDiagnosticClient:
    client = DockerDiagnosticClient(allowlist=allowlist)
    docker_client = MagicMock()
    containers = []
    for name in names:
        container = MagicMock()
        container.name = name
        container.short_id = name[:12]
        container.status = "running"
        container.image.tags = ["img:latest"]
        container.attrs = {
            "Name": f"/{name}",
            "State": {"Status": "running"},
            "RestartCount": 0,
            "NetworkSettings": {"Ports": {}},
        }
        container.logs.return_value = b"ok\n"
        containers.append(container)
    docker_client.containers.list.return_value = containers

    def _get(name: str):
        for container in containers:
            if container.name == name or container.name.lstrip("/") == name.lstrip("/"):
                return container
        raise Exception("not found")

    docker_client.containers.get.side_effect = _get
    client.client = docker_client
    return client


def test_list_containers_filters_to_allowlist():
    client = _client_with_containers(
        ["zyrabit-api", "host-unrelated", "zyrabit-db"],
        ["zyrabit-*"],
    )
    listed = client.list_containers()
    names = [row["name"] for row in listed]
    assert names == ["zyrabit-api", "zyrabit-db"]


def test_logs_and_inspect_deny_non_allowlisted():
    client = _client_with_containers(["zyrabit-api", "evil"], ["zyrabit-*"])
    denied_logs = client.get_container_logs("evil")
    assert "not in DOCKER_MCP_CONTAINER_ALLOWLIST" in denied_logs

    denied_inspect = client.inspect_container("evil")
    assert "error" in denied_inspect
    assert "not in DOCKER_MCP_CONTAINER_ALLOWLIST" in denied_inspect["error"]

    allowed_logs = client.get_container_logs("zyrabit-api")
    assert allowed_logs == "ok\n"
